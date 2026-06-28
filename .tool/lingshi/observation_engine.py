# -*- coding: utf-8 -*-
"""
灵台灵识 - 自动归纳层（Observation Engine）
===========================================
基于 Hindsight 设计，save 后自动总结模式。

功能：
- save 后自动提取主题/关键词
- 与已有观察匹配（增量更新）
- 积累阈值后创建新观察
- 持久化存储观察
"""

import os
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


class Observation:
    """观察条目"""
    
    def __init__(self, topic: str, facts: List[dict] = None, confidence: float = 0.5):
        self.topic = topic
        self.facts = facts or []
        self.confidence = confidence
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.summary = ""
    
    def add_fact(self, content: str, source: str):
        """添加事实（自动去重）"""
        # 去重：检查最后5条事实是否相同
        for fact in self.facts[-5:]:
            if fact["content"] == content:
                return  # 重复，跳过
        self.facts.append({
            "content": content,
            "source": source,
            "added_at": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()
        # 更新置信度（事实越多，置信度越高）
        self.confidence = min(1.0, 0.3 + len(self.facts) * 0.1)
    
    def needs_update(self) -> bool:
        """是否需要重新归纳"""
        return len(self.facts) >= 3 and not self.summary
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "topic": self.topic,
            "facts": self.facts,
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """从字典创建"""
        obs = cls(
            topic=data["topic"],
            facts=data.get("facts", []),
            confidence=data.get("confidence", 0.5),
        )
        obs.summary = data.get("summary", "")
        obs.created_at = data.get("created_at", datetime.now().isoformat())
        obs.updated_at = data.get("updated_at", datetime.now().isoformat())
        return obs


class ObservationEngine:
    """自动归纳引擎"""
    
    def __init__(self, vault_path: str = None):
        """
        初始化
        
        Args:
            vault_path: 灵台vault路径
        """
        if vault_path is None:
            self.vault_path = r"os.environ.get("LINGTAI_VAULT", "")"
        else:
            self.vault_path = vault_path
        
        # 存储路径
        self.store_dir = Path(__file__).parent / "observation"
        self.store_dir.mkdir(exist_ok=True)
        self.store_path = self.store_dir / "observations.json"
        
        # 配置
        self.threshold = 2  # 积累2条相关事实后归纳
        self.similarity_threshold = 0.2  # 与已有观察匹配的阈值
        
        # 加载观察
        self.observations = self._load_observations()
        self.pending = self._load_pending()
    
    def _load_observations(self) -> List[Observation]:
        """加载已有观察"""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [Observation.from_dict(obs) for obs in data.get("observations", [])]
            except Exception:
                pass
        return []
    
    def _load_pending(self) -> Dict[str, List[dict]]:
        """加载待归纳的积累槽"""
        pending_path = self.store_dir / "pending.json"
        if pending_path.exists():
            try:
                with open(pending_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_observations(self):
        """保存观察"""
        data = {
            "observations": [obs.to_dict() for obs in self.observations],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_pending(self):
        """保存待归纳"""
        pending_path = self.store_dir / "pending.json"
        with open(pending_path, "w", encoding="utf-8") as f:
            json.dump(self.pending, f, ensure_ascii=False, indent=2)
    
    def _extract_topic(self, content: str, category: str = "") -> str:
        """提取主题"""
        # 提取关键词
        keywords = []
        
        # 中文关键词（2-4字，跳过常见停用词）
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        for word in chinese_words:
            if word not in stop_words:
                keywords.append(word)
        
        # 英文关键词
        english_words = re.findall(r'[a-zA-Z]{3,}', content)
        keywords.extend([w.lower() for w in english_words[:3]])
        
        # 使用前3个关键词作为主题
        topic = " ".join(keywords[:3]) if keywords else content[:20]
        
        if category:
            topic = f"{category}:{topic}"
        
        return topic
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 简单实现：Jaccard相似度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _find_matched_observation(self, topic: str) -> Optional[Observation]:
        """查找匹配的已有观察"""
        for obs in self.observations:
            similarity = self._calculate_similarity(topic, obs.topic)
            if similarity >= self.similarity_threshold:
                return obs
        return None
    
    def _get_or_create_pending(self, topic: str) -> dict:
        """获取或创建积累槽"""
        if topic not in self.pending:
            self.pending[topic] = {
                "topic": topic,
                "facts": [],
                "created_at": datetime.now().isoformat(),
            }
        return self.pending[topic]
    
    def _归纳(self, pending: dict) -> Observation:
        """归纳积累槽为观察"""
        obs = Observation(topic=pending["topic"])
        for fact in pending.get("facts", []):
            obs.add_fact(fact["content"], fact.get("source", ""))
        
        # 简单归纳：合并所有事实作为摘要
        if obs.facts:
            contents = [f["content"] for f in obs.facts]
            obs.summary = "；".join(contents[:3])
        
        return obs
    
    def _re归纳(self, observation: Observation):
        """重新归纳观察"""
        # 简单实现：更新摘要
        if observation.facts:
            contents = [f["content"] for f in observation.facts]
            observation.summary = "；".join(contents[:3])
            observation.updated_at = datetime.now().isoformat()
    
    def on_save(self, content: str, category: str = "", source: str = "") -> dict:
        """
        save 后调用，触发自动归纳
        
        Args:
            content: 保存的内容
            category: 分类
            source: 来源
        
        Returns:
            dict: 归纳结果
        """
        # 1. 提取主题
        topic = self._extract_topic(content, category)
        
        # 2. 查找匹配的已有观察
        matched = self._find_matched_observation(topic)
        
        if matched:
            # 3a. 已有相关观察 → 增量更新
            matched.add_fact(content, source)
            if matched.needs_update():
                self._re归纳(matched)
            self._save_observations()
            return {
                "action": "updated",
                "topic": matched.topic,
                "confidence": matched.confidence,
                "facts_count": len(matched.facts),
            }
        else:
            # 3b. 无匹配 → 新开一个积累槽
            pending = self._get_or_create_pending(topic)
            pending["facts"].append({
                "content": content,
                "source": source,
                "added_at": datetime.now().isoformat(),
            })
            
            # 检查是否达到阈值
            if len(pending["facts"]) >= self.threshold:
                new_obs = self._归纳(pending)
                self.observations.append(new_obs)
                del self.pending[topic]
                self._save_observations()
                self._save_pending()
                return {
                    "action": "created",
                    "topic": new_obs.topic,
                    "confidence": new_obs.confidence,
                    "facts_count": len(new_obs.facts),
                }
            else:
                self._save_pending()
                return {
                    "action": "accumulating",
                    "topic": topic,
                    "facts_count": len(pending["facts"]),
                    "threshold": self.threshold,
                }
    
    def query(self, keyword: str) -> List[dict]:
        """
        查询观察
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            list: 匹配的观察列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        for obs in self.observations:
            if keyword_lower in obs.topic.lower() or keyword_lower in obs.summary.lower():
                results.append(obs.to_dict())
        
        return results
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_observations": len(self.observations),
            "total_pending": sum(len(facts) for facts in self.pending.values()),
            "pending_topics": len(self.pending),
            "avg_confidence": sum(obs.confidence for obs in self.observations) / max(len(self.observations), 1),
        }


# 便捷函数
def create_observation_engine(vault_path: str = None) -> ObservationEngine:
    """创建观察引擎实例"""
    return ObservationEngine(vault_path)


if __name__ == "__main__":
    # 测试
    engine = ObservationEngine()
    
    print("观察引擎测试")
    print("=" * 50)
    
    # 模拟 save 操作
    test_cases = [
        ("Python代码要简洁，避免过度封装", "技术", "对话"),
        ("用户批评了某段代码的if嵌套太深", "技术", "对话"),
        ("用户推荐了PEP 8风格指南", "技术", "对话"),
    ]
    
    for content, category, source in test_cases:
        print(f"\n保存: {content}")
        result = engine.on_save(content, category, source)
        print(f"  结果: {result}")
    
    # 查询观察
    print("\n查询观察:")
    results = engine.query("Python")
    print(f"  找到 {len(results)} 条观察")
    for obs in results:
        print(f"  - {obs['topic']}: {obs['summary'][:50]}...")
    
    # 统计
    stats = engine.get_stats()
    print(f"\n统计: {stats}")
    
    print("\n✅ 测试完成")
