# -*- coding: utf-8 -*-
"""
灵台灵识 - 混合处理模块
========================
本地处理 + LLM增强的混合模式。

设计原则：
- 简单任务：本地处理（零API成本）
- 复杂任务：LLM增强（高质量）
- 自动判断：根据任务复杂度选择处理方式

API限制应对：
- 5小时1500次调用 → 本地处理减少调用
- 上下文过长 → 本地预处理缩短文本
- 429限速 → 本地缓存 + 退避重试
"""

import os
import sys
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_engine import MemoryEngine


class HybridProcessor:
    """灵台灵识混合处理器"""
    
    def __init__(self, vault_path: str = None):
        """
        初始化混合处理器
        
        Args:
            vault_path: 灵台vault路径
        """
        if vault_path is None:
            self.vault_path = r"os.environ.get("LINGTAI_VAULT", "")"
        else:
            self.vault_path = vault_path
        
        self.memory = MemoryEngine(self.vault_path)
        self.cache_dir = Path(__file__).parent / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # 缓存过期时间（24小时）
        self.cache_ttl = 86400
    
    def _get_cache_key(self, text: str, operation: str) -> str:
        """生成缓存键"""
        content = f"{operation}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached(self, cache_key: str) -> Optional[dict]:
        """获取缓存"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 检查缓存是否过期
                if datetime.now().timestamp() - data.get("timestamp", 0) < self.cache_ttl:
                    return data.get("result")
            except Exception:
                pass
        return None
    
    def _set_cached(self, cache_key: str, result: dict):
        """设置缓存"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "result": result,
                    "timestamp": datetime.now().timestamp()
                }, f, ensure_ascii=False)
        except Exception:
            pass
    
    # ==================== 原料分级系统 ====================
    
    def classify_raw_material(self, content: str) -> str:
        """
        原料分级（本地处理，零API成本）
        
        Args:
            content: 原料内容
        
        Returns:
            str: 原料类型（simple_fact/definition/analysis/innovation）
        """
        # 清理元数据（frontmatter、创建时间等）
        clean_content = re.sub(r'^---.*?---', '', content, flags=re.DOTALL)
        clean_content = re.sub(r'创建于：.*?\n', '', clean_content)
        clean_content = re.sub(r'^#.*$', '', clean_content, flags=re.MULTILINE)
        
        # 简单事实：包含日期/数字/人名
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', clean_content):  # 日期
            return "simple_fact"
        if re.search(r'\d+[%元个万人]', clean_content):  # 数字+单位
            return "simple_fact"
        if re.search(r'(负责人|经理|主管|总监|CEO|CTO)', clean_content):  # 人名/职位
            return "simple_fact"
        
        # 框架创新：优先检查（包含"新"、"创新"、"模型"等关键词）
        if re.search(r'(全新|创新|新框架|新模型|新理论|新范式|重新定义|范式)', clean_content):
            return "innovation"
        
        # 分析论证：包含"因为"、"所以"、"分析"、多段落结构
        if re.search(r'(因为|所以|分析|论证|原因|因此|导致)', clean_content):
            return "analysis"
        if clean_content.count('##') >= 3:  # 多个章节
            return "analysis"
        if len(clean_content) > 500:  # 长文本
            return "analysis"
        
        # 概念定义：包含"是"、"定义"、"概念"
        if re.search(r'(是|定义为|概念|指|意味着)', clean_content):
            return "definition"
        
        return "definition"  # 默认
    
    def get_threshold_for_grade(self, grade: str) -> float:
        """
        根据原料分级获取阈值
        
        Args:
            grade: 原料类型
        
        Returns:
            float: 阈值（0-1）
        """
        thresholds = {
            "simple_fact": 0.6,    # 简单事实：高阈值，多用本地
            "definition": 0.4,     # 概念定义：中阈值
            "analysis": 0.2,       # 分析论证：低阈值，多用LLM
            "innovation": 0.0,     # 框架创新：最低阈值，必须用LLM
        }
        return thresholds.get(grade, 0.3)
    
    def get_grade_description(self, grade: str) -> dict:
        """
        获取原料分级描述
        
        Args:
            grade: 原料类型
        
        Returns:
            dict: 分级描述
        """
        descriptions = {
            "simple_fact": {
                "name": "简单事实",
                "description": "日期、数字、人名等具体事实",
                "threshold": 0.6,
                "method": "本地处理为主",
            },
            "definition": {
                "name": "概念定义",
                "description": "术语、定义、解释等概念性内容",
                "threshold": 0.4,
                "method": "本地处理为主",
            },
            "analysis": {
                "name": "分析论证",
                "description": "有逻辑、有引用的分析性内容",
                "threshold": 0.2,
                "method": "LLM增强为主",
            },
            "innovation": {
                "name": "框架创新",
                "description": "新观点、新模型、新理论",
                "threshold": 0.0,
                "method": "必须用LLM",
            },
        }
        return descriptions.get(grade, descriptions["definition"])
    
    # ==================== 本地处理函数 ====================
    
    def local_coverage_check(self, raw_content: str, target_content: str) -> dict:
        """
        本地覆盖判断（替代LLM调用）
        
        Args:
            raw_content: 原料内容
            target_content: 目标页内容
        
        Returns:
            dict: 覆盖判断结果
        """
        # 提取关键词
        raw_keywords = self._extract_keywords(raw_content)
        target_keywords = self._extract_keywords(target_content)
        
        # 计算重叠率
        if not raw_keywords or not target_keywords:
            return {"coverage": "未知", "overlap": 0, "action": "补角"}
        
        overlap = len(raw_keywords & target_keywords) / len(raw_keywords)
        
        # 判断覆盖程度（降低阈值，更多使用本地处理）
        if overlap > 0.6:
            return {"coverage": "已包含", "overlap": overlap, "action": "跳过"}
        elif overlap > 0.3:
            return {"coverage": "部分覆盖", "overlap": overlap, "action": "补强"}
        elif overlap > 0.1:
            return {"coverage": "少量重叠", "overlap": overlap, "action": "补角"}
        else:
            return {"coverage": "无重叠", "overlap": overlap, "action": "新页"}
    
    def local分流判断(self, raw_content: str, target_pages: list) -> dict:
        """
        本地分流判断（替代LLM调用）
        
        Args:
            raw_content: 原料内容
            target_pages: 目标页列表
        
        Returns:
            dict: 分流建议
        """
        raw_keywords = self._extract_keywords(raw_content)
        
        # 找到最相关的目标页
        best_match = None
        best_score = 0
        
        for page in target_pages:
            page_keywords = self._extract_keywords(page.get("summary", "") + page.get("title", ""))
            
            if not raw_keywords or not page_keywords:
                continue
            
            overlap = len(raw_keywords & page_keywords) / len(raw_keywords)
            
            if overlap > best_score:
                best_score = overlap
                best_match = page
        
        # 判断分流类型
        if best_score > 0.7:
            return {"type": "补强", "target": best_match, "score": best_score}
        elif best_score > 0.3:
            return {"type": "补角", "target": best_match, "score": best_score}
        else:
            return {"type": "新页", "target": None, "score": best_score}
    
    def local_pinji_check(self, content: str, backlinks: int = 0) -> str:
        """
        本地品级判断（替代LLM调用）
        
        Args:
            content: 页面内容
            backlinks: 入链数
        
        Returns:
            str: 品级（上品/中品/下品）
        """
        # 上品：被≥3页内联引用
        if backlinks >= 3:
            return "上品"
        
        # 中品：有对比/交叉/矛盾标注
        if "对比" in content or "交叉" in content or "矛盾" in content or "⚡" in content:
            return "中品"
        
        # 下品：单源摘要
        return "下品"
    
    def local_extract_keywords(self, text: str, max_keywords: int = 10) -> set:
        """本地关键词提取"""
        keywords = set()
        
        # 中文关键词（2-4字）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        keywords.update(chinese_words[:max_keywords])
        
        # 英文关键词
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        keywords.update([w.lower() for w in english_words[:5]])
        
        return keywords
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词（内部方法）"""
        return self.local_extract_keywords(text)
    
    # ==================== LLM增强函数 ====================
    
    def llm_analyze(self, text: str) -> dict:
        """
        LLM分析（带缓存）
        
        Args:
            text: 待分析的文本
        
        Returns:
            dict: 分析结果
        """
        # 检查缓存
        cache_key = self._get_cache_key(text, "analyze")
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # 调用LLM
        try:
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            result = engine.analyze(text)
            
            # 缓存结果
            self._set_cached(cache_key, result)
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def llm_summarize(self, text: str, max_length: int = 200) -> str:
        """
        LLM总结（带缓存）
        
        Args:
            text: 待总结的文本
            max_length: 最大长度
        
        Returns:
            str: 总结结果
        """
        # 检查缓存
        cache_key = self._get_cache_key(text, "summarize")
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # 调用LLM
        try:
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            result = engine.summarize(text, max_length)
            
            # 缓存结果
            self._set_cached(cache_key, result)
            
            return result
        except Exception as e:
            return f"[错误: {e}]"
    
    # ==================== 混合处理函数 ====================
    
    def hybrid_distill(self, raw_content: str, target_pages: list) -> dict:
        """
        混合提炼：原料分级 + 本地预处理 + LLM增强
        
        Args:
            raw_content: 原料内容
            target_pages: 目标页列表
        
        Returns:
            dict: 提炼结果
        """
        # 第一步：原料分级（零API成本）
        grade = self.classify_raw_material(raw_content)
        grade_info = self.get_grade_description(grade)
        threshold = self.get_threshold_for_grade(grade)
        
        # 第二步：本地预处理（零API成本）
        coverage = self.local_coverage_check(raw_content, "")
        分流 = self.local分流判断(raw_content, target_pages)
        
        # 第三步：根据原料分级和置信度决定是否调用LLM
        if 分流["score"] > threshold:
            # 高于阈值：本地处理即可
            return {
                "type": 分流["type"],
                "target": 分流["target"],
                "method": "local",
                "coverage": coverage,
                "confidence": 分流["score"],
                "grade": grade,
                "grade_info": grade_info,
                "threshold": threshold,
            }
        else:
            # 低于阈值：调用LLM增强
            try:
                llm_result = self.llm_analyze(raw_content)
                return {
                    "type": 分流["type"],
                    "target": 分流["target"],
                    "method": "llm",
                    "coverage": coverage,
                    "llm_analysis": llm_result,
                    "confidence": 分流["score"],
                    "grade": grade,
                    "grade_info": grade_info,
                    "threshold": threshold,
                }
            except Exception as e:
                # LLM失败：回退到本地处理
                return {
                    "type": 分流["type"],
                    "target": 分流["target"],
                    "method": "local_fallback",
                    "coverage": coverage,
                    "error": str(e),
                    "confidence": 分流["score"],
                    "grade": grade,
                    "grade_info": grade_info,
                    "threshold": threshold,
                }
    
    def hybrid_summarize(self, text: str, max_length: int = 200) -> dict:
        """
        混合总结：本地预处理 + LLM增强
        
        Args:
            text: 待总结的文本
            max_length: 最大长度
        
        Returns:
            dict: 总结结果
        """
        # 本地预处理：提取关键句
        local_summary = self._local_extract_key_sentences(text, max_length)
        
        # 如果本地摘要足够好，直接返回
        if len(local_summary) > max_length * 0.8:
            return {
                "summary": local_summary[:max_length],
                "method": "local",
            }
        
        # 否则调用LLM增强
        try:
            llm_summary = self.llm_summarize(text, max_length)
            return {
                "summary": llm_summary,
                "method": "llm",
            }
        except Exception as e:
            # LLM失败：使用本地摘要
            return {
                "summary": local_summary[:max_length],
                "method": "local_fallback",
                "error": str(e),
            }
    
    def _local_extract_key_sentences(self, text: str, max_length: int) -> str:
        """本地提取关键句"""
        # 按句号分割
        sentences = re.split(r'[。！？]', text)
        
        # 选择最重要的句子（前几句）
        key_sentences = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) > max_length:
                break
            
            key_sentences.append(sentence)
            current_length += len(sentence)
        
        return "。".join(key_sentences) + "。" if key_sentences else text[:max_length]
    
    # ==================== 统计 ====================
    
    def get_stats(self) -> dict:
        """获取混合处理统计"""
        # 统计缓存文件
        cache_files = list(self.cache_dir.glob("*.json"))
        
        return {
            "cache_size": len(cache_files),
            "cache_dir": str(self.cache_dir),
        }


# 便捷函数
def create_hybrid_processor(vault_path: str = None) -> HybridProcessor:
    """创建混合处理器实例"""
    return HybridProcessor(vault_path)
