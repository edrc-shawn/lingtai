# -*- coding: utf-8 -*-
"""
灵台灵识 - 感知模块（工具层）
============================
只提供工具，不包含检测逻辑。
检测逻辑由 IDENTITY.md 规则驱动，AI 自己判断。

工具：
- inject: 注入相关知识
- save: 保存新知识（触发观察引擎）
- recommend: 推荐相关页面
- context: 生成上下文
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_engine import MemoryEngine
from observation_engine import ObservationEngine


class PerceptionTools:
    """灵台灵识感知工具"""
    
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
        
        self.memory = MemoryEngine(self.vault_path)
        self.observation = ObservationEngine(self.vault_path)
        self.raw_dir = Path(self.vault_path) / "原料"
        self.danfang_dir = Path(self.vault_path) / "丹房"
    
    def inject(self, keyword: str) -> dict:
        """
        注入相关知识（AI调用）
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            dict: 匹配的知识（按品级降序）
        """
        query_result = self.memory.query(keyword)
        
        # memory.query() 现在返回 dict: {"results": [...], "match_type": "...", "keyword": "..."}
        results = query_result.get("results", [])
        
        if not results:
            return {"found": False, "match_type": query_result.get("match_type", "none")}
        
        # 按品级排序（上品 > 中品 > 下品 > 无品级）
        pinji_order = {"上品": 0, "中品": 1, "下品": 2, "": 3}
        results.sort(key=lambda r: pinji_order.get(r.get("pinji", ""), 3))
        
        return {
            "found": True,
            "match_type": query_result.get("match_type", "exact"),
            "results": [
                {
                    "path": r["path"],
                    "title": r["title"],
                    "summary": r.get("summary", "")[:200],
                    "pinji": r.get("pinji", ""),  # 台律：附带品级标签
                }
                for r in results[:5]
            ],
        }
    
    def save(self, content: str, category: str = "", source: str = "对话") -> dict:
        """
        保存新知识到原料目录（AI调用）
        
        Args:
            content: 知识内容
            category: 分类（可选）
            source: 来源（默认：对话）
        
        Returns:
            dict: 保存结果
        """
        # 生成文件名
        now = datetime.now()
        date_str = now.strftime("%Y%m%d-%H%M%S")
        
        # 清理内容作为文件名（台律：文件名禁止弯/直引号）
        title = content[:30].replace("\n", " ").strip()
        title = re.sub(r'[<>:"/\\|?*\u201c\u201d\u0022]', '', title)  # 移除非法字符 + 引号
        
        filename = f"{title}-{date_str}.md"
        filepath = self.raw_dir / filename
        
        # 自动推断域（通过 query 命中页面的 domain）
        domain = ""
        keyword = content[:50].replace("\n", " ").strip()[:30]
        try:
            qr = self.memory.query(keyword)
            results = qr.get("results", []) if isinstance(qr, dict) else qr
            if results:
                domain = results[0].get("domain", "")
        except Exception:
            pass

        # 生成frontmatter
        fm = f"""---
处理状态: 待提炼
来源: {source}
日期: {now.strftime('%Y-%m-%d')}
"""
        if domain:
            fm += f"域: {domain}\n"
        fm += "---\n"
        
        # 写入文件
        try:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(fm + "\n" + content)
            
            # 触发观察引擎
            obs_result = self.observation.on_save(content, category, source)
            
            # 生成观察反馈消息
            feedback = None
            if obs_result.get("action") == "created":
                feedback = f"灵识观察：已归纳新观察「{obs_result.get('topic', '')}」（置信度: {obs_result.get('confidence', 0):.0%}）"
            elif obs_result.get("action") == "updated":
                feedback = f"灵识观察：已更新观察「{obs_result.get('topic', '')}」（现有{obs_result.get('facts_count', 0)}条事实）"
            elif obs_result.get("action") == "accumulating":
                facts_count = obs_result.get('facts_count', 0)
                threshold = obs_result.get('threshold', 3)
                if facts_count >= threshold - 1:  # 接近阈值时提示
                    feedback = f"灵识观察：「{obs_result.get('topic', '')}」已有{facts_count}条事实，即将归纳（需{threshold}条）"
            
            return {
                "success": True,
                "path": str(filepath.relative_to(Path(self.vault_path))),
                "filename": filename,
                "observation": obs_result,
                "observation_feedback": feedback,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def recommend(self, current_topic: str, max_results: int = 5) -> dict:
        """
        推荐相关页面（AI调用）
        
        Args:
            current_topic: 当前话题
            max_results: 最大结果数
        
        Returns:
            dict: 推荐结果（按品级降序）
        """
        # 提取关键词
        keywords = self._extract_keywords(current_topic)
        
        # 搜索相关页面
        all_results = []
        for keyword in keywords[:3]:
            query_result = self.memory.query(keyword)
            # memory.query() 返回 dict，需要取 "results" 字段
            results = query_result.get("results", [])
            all_results.extend(results)
        
        # 去重
        seen_paths = set()
        unique_results = []
        for r in all_results:
            if r["path"] not in seen_paths:
                seen_paths.add(r["path"])
                unique_results.append(r)
        
        if not unique_results:
            return {"found": False}
        
        # 按品级排序（台律：上品优先）
        pinji_order = {"上品": 0, "中品": 1, "下品": 2, "": 3}
        unique_results.sort(key=lambda r: pinji_order.get(r.get("pinji", ""), 3))
        
        return {
            "found": True,
            "recommendations": [
                {
                    "path": r["path"],
                    "title": r["title"],
                    "summary": r.get("summary", "")[:100],
                    "pinji": r.get("pinji", ""),  # 台律：附带品级标签
                }
                for r in unique_results[:max_results]
            ],
        }
    
    def context(self) -> dict:
        """
        生成会话上下文（AI调用）
        融合 hook-session-greeting 和 hook-pre-compact-summary 功能
        
        Returns:
            dict: 上下文摘要
        """
        import os
        from datetime import datetime, timedelta
        
        stats = self.memory.get_stats()
        
        # 1. 知识库概览（原有功能）
        overview = {
            "total_pages": stats["total_pages"],
            "total_links": stats["total_links"],
            "domains": stats["by_domain"],
        }
        
        # 2. 待办概要（来自 hook-session-greeting）
        pending_dir = Path(self.vault_path) / "原料"
        pending_count = 0
        if pending_dir.exists():
            for f in pending_dir.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8")
                    if "处理状态: 待提炼" in content:
                        pending_count += 1
                except:
                    pass
        
        # 3. 最近更新（来自 hook-session-greeting）
        recent_pages = sorted(
            self.memory.pages,
            key=lambda p: p.get("date", ""),
            reverse=True
        )[:5]
        
        # 4. 核心页面（高入链）
        hub_pages = sorted(
            self.memory.pages,
            key=lambda p: len(p.get("linked_from", [])),
            reverse=True
        )[:5]
        
        # 5. 生成问候语（来自 hook-session-greeting）
        now = datetime.now()
        greeting = f"今天是 {now.strftime('%Y年%m月%d日')}，{['星期一','星期二','星期三','星期四','星期五','星期六','星期日'][now.weekday()]}。"
        
        return {
            "greeting": greeting,
            "overview": overview,
            "pending_count": pending_count,
            "recent_pages": [
                {"path": p["path"], "title": p["title"], "date": p.get("date", "")}
                for p in recent_pages
            ],
            "hub_pages": [
                {"path": p["path"], "title": p["title"], "backlinks": len(p.get("linked_from", []))}
                for p in hub_pages
            ],
            "message": f"知识库有 {stats['total_pages']} 个页面，{pending_count} 篇待提炼原料。" if pending_count > 0 else f"知识库有 {stats['total_pages']} 个页面，无待提炼原料。",
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 中文关键词（2-4字）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        keywords.extend(chinese_words[:10])
        
        # 英文关键词
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        keywords.extend([w.lower() for w in english_words[:5]])
        
        # 去重
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]


# 便捷函数
def create_perception_tools(vault_path: str = None) -> PerceptionTools:
    """创建感知工具实例"""
    return PerceptionTools(vault_path)
