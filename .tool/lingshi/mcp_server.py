# -*- coding: utf-8 -*-
"""
灵台知识库 MCP Server
====================
让 MiMo Code 等工具能够访问灵台知识库。

工具列表：
- query: 查询知识库
- search: 搜索页面内容
- analyze: 分析页面链接
- related: 获取相关页面
- stats: 获取知识库统计
- domains: 获取域列表
- pages: 获取页面列表
- check_inject: 检查是否需要知识注入
- check_learn: 检查是否需要自动学习
- check_recommend: 检查是否需要关联推荐
- generate_context: 生成会话上下文
"""

import os
import sys
import json
import importlib
from pathlib import Path
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_engine import MemoryEngine
from auto_edge import AutoEdge
from perception import PerceptionTools
from kar_fusion import KARFusion
from perception_stats import PerceptionStats
from reasoning_engine import ReasoningEngine
from rules import LingtaiRules
from observation_engine import ObservationEngine

# Tavily 搜索配置
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_MONTHLY_LIMIT = 1000
_tavily_month = ""
_tavily_count = 0
from user_profile import UserProfile
import os
from skillopt.evolve_engine import EvolveEngine
from skillopt.stager import Stager
from skillopt.pattern_detector import PatternDetector
from skillopt.confidence_scorer import ConfidenceScorer


# 配置
VAULT_PATH = os.environ.get("LINGTAI_VAULT", r"os.environ.get("LINGTAI_VAULT", "")")


class LingtaiMCPServer:
    """灵台知识库 MCP Server"""
    
    def __init__(self):
        self.memory = MemoryEngine(VAULT_PATH)
        self.auto_edge = AutoEdge(VAULT_PATH)
        self.perception = PerceptionTools(VAULT_PATH)
        self.kar = KARFusion(VAULT_PATH)
        self.perception_stats_monitor = PerceptionStats()
        self.reasoning = ReasoningEngine()
        self.rules_engine = LingtaiRules(VAULT_PATH)
        self.observation = ObservationEngine(VAULT_PATH)
        self.user_profile = UserProfile(VAULT_PATH)
        self.skillopt_engine = EvolveEngine(VAULT_PATH)
        self.skillopt_stager = Stager()
        self.skillopt_detector = PatternDetector()
        self.skillopt_scorer = ConfidenceScorer()
    
    def query(self, keyword: str, hops: int = 2, category: str = "") -> dict:
        """
        查询知识库
        
        Args:
            keyword: 搜索关键词
            hops: 图扩散跳数（默认2）
            category: 域分类筛选（如"00-思考与认知"，可选）
        
        Returns:
            dict: 查询结果
        """
        self.user_profile.record_query(keyword)
        for r in self.memory.query(keyword).get("results", []):
            if r.get("domain"):
                self.user_profile.record_interest(r["domain"])

        # 直接查询
        query_result = self.memory.query(keyword)
        direct_results = query_result.get("results", []) if isinstance(query_result, dict) else query_result
        

        # 按分类筛选
        if category:
            direct_results = [r for r in direct_results if r.get("domain", "") == category]
        # 图扩散搜索
        graph_results = self.memory.search_graph(keyword, hops=hops)

        # 近期记忆：查询 hook-summaries（最近2天卡片）
        recent_memories = self._search_hook_summaries(keyword)

        return {
            "keyword": keyword,
            "direct_matches": len(direct_results),
            "related_knowledge": len(graph_results),
            "recent_memories": len(recent_memories),
            "results": [
                {
                    "path": p["path"],
                    "title": p["title"],
                    "summary": p.get("summary", "")[:100],
                    "domain": p.get("domain", ""),
                    "tags": p.get("tags", []),
                }
                for p in direct_results[:10]
            ],
            "related": [
                {
                    "path": p["path"],
                    "title": p["title"],
                    "summary": p.get("summary", "")[:100],
                }
                for p in graph_results[:10]
            ],
            "recent": [
                {
                    "path": m["path"],
                    "title": m["title"],
                    "summary": m["summary"][:150],
                    "date": m["date"],
                }
                for m in recent_memories[:5]
            ],
        }

    def _search_hook_summaries(self, keyword: str) -> list:
        """搜索钩子摘要卡片（近期记忆）"""
        vault = os.environ.get("LINGTAI_VAULT", r"os.environ.get("LINGTAI_VAULT", "")")
        summaries_dir = os.path.join(vault, ".tool", "hook-summaries")
        if not os.path.isdir(summaries_dir):
            return []

        from datetime import datetime, timedelta
    
        results = []
        now = datetime.now()
        keyword_lower = keyword.lower()

        for fname in os.listdir(summaries_dir):
            fpath = os.path.join(summaries_dir, fname)
            if not fname.endswith('.md') or not os.path.isfile(fpath):
                continue

            # 只读最近 2 天
            try:
                date_part = fname.replace('.md', '')[:10]
                fdate = datetime.strptime(date_part, '%Y-%m-%d')
                if (now - fdate) > timedelta(days=2):
                    continue
            except ValueError:
                continue

            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 关键词匹配
            if keyword_lower not in content.lower():
                continue

            lines = content.strip().split('\n')
            title = fname.replace('.md', '')
            summary = content[:200].replace('\n', ' ').strip()

            results.append({
                "path": f".tool/hook-summaries/{fname}",
                "title": title,
                "summary": summary,
                "date": date_part,
            })

        return results
    
    def search(self, keyword: str, search_content: bool = False) -> dict:
        """
        搜索页面内容
        
        Args:
            keyword: 搜索关键词
            search_content: 是否搜索页面内容（较慢）
        
        Returns:
            dict: 搜索结果
        """
        # 搜索摘要
        summary_results = self.memory.search_by_summary(keyword)
        
        # 搜索内容
        content_results = []
        if search_content:
            content_results = self.memory.search_by_content(keyword)
        
        # 合并去重
        all_paths = set()
        all_results = []
        
        for p in summary_results + content_results:
            if p["path"] not in all_paths:
                all_paths.add(p["path"])
                all_results.append(p)
        
        return {
            "keyword": keyword,
            "summary_matches": len(summary_results),
            "content_matches": len(content_results),
            "total_matches": len(all_results),
            "results": [
                {
                    "path": p["path"],
                    "title": p["title"],
                    "summary": p.get("summary", "")[:100],
                }
                for p in all_results[:20]
            ],
        }
    
    def analyze(self, page_path: str) -> dict:
        """
        分析页面链接
        
        Args:
            page_path: 页面路径（如 "丹房/00-思考与认知/含人量"）
        
        Returns:
            dict: 分析结果
        """
        # 获取相关页面
        related = self.memory.get_related_pages(page_path)
        
        # 获取潜在关联
        potential = self.auto_edge.find潜在关联(page_path)
        
        # 获取链接建议
        suggestions = self.auto_edge.get_link_suggestions(page_path)
        
        return {
            "page": page_path,
            "related_count": len(related),
            "related_pages": [
                {"path": p["path"], "title": p["title"]}
                for p in related[:10]
            ],
            "potential_count": len(potential),
            "potential_pages": [
                {"path": p["path"], "title": p["title"]}
                for p in potential[:10]
            ],
            "suggestions": suggestions[:5],
        }
    
    def related(self, page_path: str, max_results: int = 10) -> dict:
        """
        获取相关页面
        
        Args:
            page_path: 页面路径
            max_results: 最大结果数
        
        Returns:
            dict: 相关页面列表
        """
        related = self.memory.get_related_pages(page_path, max_results)
        
        return {
            "page": page_path,
            "count": len(related),
            "related": [
                {
                    "path": p["path"],
                    "title": p["title"],
                    "summary": p.get("summary", "")[:100],
                    "backlinks": len(p.get("linked_from", [])),
                }
                for p in related
            ],
        }
    
    def stats(self) -> dict:
        """
        获取知识库统计
        
        Returns:
            dict: 统计信息
        """
        memory_stats = self.memory.get_stats()
        edge_analysis = self.auto_edge.analyze_links()
        
        return {
            "total_pages": memory_stats["total_pages"],
            "total_links": memory_stats["total_links"],
            "core_pages": memory_stats["core_pages"],
            "gate_pages": memory_stats["gate_pages"],
            "isolated_pages": memory_stats["isolated_pages"],
            "domains": memory_stats["by_domain"],
            "pinji": memory_stats["by_pinji"],
            "hub_pages": edge_analysis["hub_pages"][:5],
        }
    
    def domains(self) -> dict:
        """
        获取域列表
        
        Returns:
            dict: 域列表和页面数
        """
        stats = self.memory.get_stats()
        
        return {
            "domains": [
                {"name": name, "count": count}
                for name, count in stats["by_domain"].items()
            ],
            "total": len(stats["by_domain"]),
        }
    
    def pages(self, domain: str = None, limit: int = 50) -> dict:
        """
        获取页面列表
        
        Args:
            domain: 域名（可选，不传则返回所有）
            limit: 最大返回数
        
        Returns:
            dict: 页面列表
        """
        if domain:
            pages = self.memory.get_pages_by_domain(domain)
        else:
            pages = self.memory.pages
        
        return {
            "domain": domain or "all",
            "count": len(pages),
            "pages": [
                {
                    "path": p["path"],
                    "title": p["title"],
                    "domain": p.get("domain", ""),
                    "pinji": p.get("pinji", ""),
                    "backlinks": len(p.get("linked_from", [])),
                }
                for p in pages[:limit]
            ],
        }
    
    def inject(self, keyword: str) -> dict:
        """
        注入相关知识
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            dict: 匹配的知识
        """
        return self.perception.inject(keyword)
    
    def save(self, content: str, category: str = "", source: str = "对话") -> dict:
        """
        保存新知识
        
        Args:
            content: 知识内容
            category: 分类（可选）
            source: 来源
        
        Returns:
            dict: 保存结果
        """
        return self.perception.save(content, category, source)

    def observations(self, keyword: str = "", limit: int = 20) -> dict:
        """
        查询自动归纳出的观察
        
        Args:
            keyword: 搜索关键词（可选，空则返回全部）
            limit: 最大返回数
        
        Returns:
            dict: 观察列表
        """
        if keyword:
            results = self.observation.query(keyword)
        else:
            results = [obs.to_dict() for obs in self.observation.observations]
        
        return {
            "total": len(results),
            "observations": results[:limit],
        }

    def observation_stats(self) -> dict:
        """
        观察层统计信息
        
        Returns:
            dict: 统计
        """
        return self.observation.get_stats()

    def hebbian_stats(self) -> dict:
        """
        Hebbian 动态权重统计，查看共现边的权重分布
        
        Returns:
            dict: 权重统计
        """
        stats = self.memory.hebbian.get_stats()
        stats["decay_days"] = self.memory.hebbian.decay_days
        return stats

    def sentinel(self) -> dict:
        """
        感知规则监控报告（Sentinel）。检查各规则的健康状态和违规情况
        
        Returns:
            dict: 监控报告（含健康状态、违规列表、统计摘要）
        """
        return self.perception_stats_monitor.get_monitoring_report()

    def tavily_search(self, keyword: str, max_results: int = 5) -> dict:
        """
        联网搜索（Tavily API）。三步检索无结果时调用，获取外部信息

        Args:
            keyword: 搜索关键词
            max_results: 返回结果数（默认5，最大10）

        Returns:
            dict: 搜索结果
        """
        global _tavily_month, _tavily_count
        from datetime import date
        this_month = str(date.today())[:7]  # "2026-06"

        # 重置每月计数
        if _tavily_month != this_month:
            _tavily_month = this_month
            _tavily_count = 0

        # 检查用量
        if _tavily_count >= TAVILY_MONTHLY_LIMIT:
            return {"error": "已超过每月搜索上限（1000次）", "results": []}

        if not TAVILY_API_KEY:
            return {"error": "未配置Tavily API密钥", "results": []}

        try:
            import requests
            resp = requests.post(TAVILY_API_URL, json={
                "api_key": TAVILY_API_KEY,
                "query": keyword,
                "max_results": min(max_results, 10),
                "search_depth": "basic"
            }, timeout=15)
            data = resp.json()
            _tavily_count += 1

            results = data.get("results", [])
            return {
                "keyword": keyword,
                "total_results": len(results),
                "usage_this_month": _tavily_count,
                "monthly_limit": TAVILY_MONTHLY_LIMIT,
                "source": "Tavily (外部网络搜索)",
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:300],
                        "score": r.get("score", 0),
                    }
                    for r in results[:max_results]
                ],
            }
        except Exception as e:
            return {"error": f"搜索失败: {e}", "results": []}

    def profile(self) -> dict:
        """
        返回用户画像（认知偏好+决策风格），让 AI 快速了解用户
        融合 WorkBuddy 全局记忆 + 灵识本地学习数据
        """
        wb_memory = os.path.expanduser("~/.workbuddy/MEMORY.md")
        wb_identity = os.path.expanduser("~/.workbuddy/IDENTITY.md")
        sections = []

        # 读 IDENTITY.md（个人背景 + 风格）
        if os.path.isfile(wb_identity):
            with open(wb_identity, "r", encoding="utf-8", errors="ignore") as f:
                sections.append({"source": "IDENTITY.md", "content": f.read()[:2000]})

        # 读 MEMORY.md（跨项目偏好）
        if os.path.isfile(wb_memory):
            with open(wb_memory, "r", encoding="utf-8", errors="ignore") as f:
                sections.append({"source": "MEMORY.md", "content": f.read()[:2000]})

        # 灵识本地学习数据
        learning = self.user_profile.get_profile_summary()

        return {
            "found": len(sections) > 0,
            "sections": sections,
            "learning": learning,
            "note": "画像由 WorkBuddy + 灵识本地学习共同维护。灵识记录查询偏好和纠正历史，越用越懂用户。",
        }

    def recommend(self, current_topic: str, max_results: int = 5) -> dict:
        """
        推荐相关页面
        
        Args:
            current_topic: 当前话题
            max_results: 最大结果数
        
        Returns:
            dict: 推荐结果
        """
        return self.perception.recommend(current_topic, max_results)
    
    def context(self) -> dict:
        """
        生成会话上下文
        
        Returns:
            dict: 上下文摘要
        """
        return self.perception.context()
    
    def graph(self, page_path: str, hops: int = 3, weighted: bool = True) -> dict:
        """
        从某页面出发的图扩散（支持加权）
        
        Args:
            page_path: 起始页面路径
            hops: 扩散跳数（默认3，最大3）
            weighted: 是否启用加权扩散（默认开启）
        
        Returns:
            dict: 扩散结果
        """
        # 限制最大跳数
        hops = min(hops, 3)
        
        # 获取起始页面
        start_page = self.memory.get_page_by_path(page_path)
        if not start_page:
            return {"found": False, "error": f"页面不存在: {page_path}"}
        
        # BFS扩散（带权重）
        visited = set()
        result_nodes = []
        queue = [(start_page, 0, 1.0)]
        
        while queue:
            current_page, current_hop, current_weight = queue.pop(0)
            
            if current_page["path"] in visited:
                continue
            if current_hop > hops:
                continue
            
            visited.add(current_page["path"])
            
            # 计算页面权重
            page_weight = self.memory._calculate_page_weight(current_page) if weighted else 1.0
            final_weight = current_weight * page_weight
            
            result_nodes.append({
                "path": current_page["path"],
                "title": current_page["title"],
                "hop": current_hop,
                "weight": round(final_weight, 3),
                "summary": current_page.get("summary", "")[:100],
            })
            
            # 找到关联页面
            for link in current_page.get("links_to", []):
                neighbor = self.memory.get_page_by_path(link)
                if neighbor and neighbor["path"] not in visited:
                    queue.append((neighbor, current_hop + 1, final_weight))
            
            # 找到被引用页面
            for link in current_page.get("linked_from", []):
                neighbor = self.memory.get_page_by_path(link)
                if neighbor and neighbor["path"] not in visited:
                    queue.append((neighbor, current_hop + 1, final_weight))
        
        # 按权重排序（加权模式）
        if weighted:
            result_nodes.sort(key=lambda x: x.get("weight", 0), reverse=True)
        
        return {
            "found": True,
            "start": page_path,
            "hops": hops,
            "weighted": weighted,
            "total_nodes": len(result_nodes),
            "nodes": result_nodes,
        }
    
    def search_logs(self, keyword: str, days: int = 7) -> dict:
        """
        搜索日志和体检记录
        
        Args:
            keyword: 搜索关键词
            days: 回溯天数（默认7天）
        
        Returns:
            dict: 搜索结果
        """
        from datetime import datetime, timedelta
        import os
        
        vault = os.environ.get("LINGTAI_VAULT", r"os.environ.get("LINGTAI_VAULT", "")")
        results = []
        
        # 搜索日志
        log_path = os.path.join(vault, "丹房", "日志.md")
        if os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                cutoff = datetime.now() - timedelta(days=days)
                keyword_lower = keyword.lower()
                for line in lines:
                    # 解析日志行日期 [YY-MM-DD HH:MM]
                    if line.startswith("|") and "[" in line:
                        try:
                            date_str = line.split("[")[1].split(" ")[0]
                            log_date = datetime.strptime(date_str, "%y-%m-%d")
                            if log_date < cutoff:
                                continue
                        except (ValueError, IndexError):
                            pass
                    if keyword_lower in line.lower():
                        results.append({
                            "source": "丹房/日志.md",
                            "content": line.strip()[:200],
                        })
            except (OSError, UnicodeDecodeError) as e:
                results.append({"error": f"读取日志失败: {e}"})
        
        # 搜索体检目录
        exam_dir = os.path.join(vault, "体检")
        if os.path.isdir(exam_dir):
            for fname in os.listdir(exam_dir):
                fpath = os.path.join(exam_dir, fname)
                if not fname.endswith((".md", ".json", ".html")) or not os.path.isfile(fpath):
                    continue
                try:
                    mtime = os.path.getmtime(fpath)
                    file_date = datetime.fromtimestamp(mtime)
                    if (datetime.now() - file_date) > timedelta(days=days):
                        continue
                except OSError:
                    pass
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if keyword.lower() in content.lower():
                        # 提取匹配片段
                        lines = content.split("\n")
                        matching_lines = [l.strip()[:150] for l in lines if keyword.lower() in l.lower()]
                        results.append({
                            "source": f"体检/{fname}",
                            "matches": len(matching_lines),
                            "snippets": matching_lines[:5],
                        })
                except (OSError, UnicodeDecodeError):
                    pass
        
        return {
            "keyword": keyword,
            "days": days,
            "total_matches": len(results),
            "results": results[:20],
            "note": "从 丹房/日志.md 和 体检/ 目录检索，按关键词匹配",
        }

    def token(self, period: str = "today") -> dict:
        """
        查询 Token 消耗
        
        Args:
            period: 时间段（today/week/month/all）
        
        Returns:
            dict: Token 统计
        """
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        from token_monitor import TokenMonitor
        
        monitor = TokenMonitor()
        
        if period == "today":
            savings = monitor.get_savings()
            return {
                "period": "today",
                "consumed": savings["today"]["consumed"],
                "saved": savings["today"]["saved"],
                "cost": savings["today"]["cost"],
                "saved_cost": savings["today"]["saved_cost"],
                "save_rate": round(savings["today"]["saved"] / max(savings["today"]["consumed"], 1) * 100, 1),
            }
        elif period == "week":
            trend = monitor.get_trend_analysis(days=7)
            return {
                "period": "week",
                "avg_daily_tokens": trend["avg_daily_tokens"],
                "avg_daily_cost": trend["avg_daily_cost"],
                "avg_daily_saved": trend["avg_daily_saved"],
                "total_tokens": trend["total_tokens"],
                "total_cost": trend["total_cost"],
                "trend": trend["trend"],
            }
        elif period == "month":
            trend = monitor.get_trend_analysis(days=30)
            return {
                "period": "month",
                "avg_daily_tokens": trend["avg_daily_tokens"],
                "avg_daily_cost": trend["avg_daily_cost"],
                "avg_daily_saved": trend["avg_daily_saved"],
                "total_tokens": trend["total_tokens"],
                "total_cost": trend["total_cost"],
                "trend": trend["trend"],
            }
        else:  # all
            savings = monitor.get_savings()
            return {
                "period": "all",
                "total_consumed": savings["total"]["consumed"],
                "total_saved": savings["total"]["saved"],
                "total_cost": savings["total"]["cost"],
                "total_saved_cost": savings["total"]["saved_cost"],
            }
    
    def unified_query(self, keyword: str, hops: int = 2) -> dict:
        """
        KAR统一查询：知识+关联+推理
        
        Args:
            keyword: 搜索关键词
            hops: 图扩散跳数
        
        Returns:
            dict: 统一查询结果
        """
        return self.kar.unified_query(keyword, hops=hops)
    
    def chain_query(self, keywords: list, hops: int = 2) -> dict:
        """
        KAR链式查询：多关键词串联
        
        Args:
            keywords: 关键词列表
            hops: 每步图扩散跳数
        
        Returns:
            dict: 链式查询结果
        """
        return self.kar.chain_query(keywords, hops=hops)
    
    def explore_topic(self, topic: str, depth: int = 2) -> dict:
        """
        KAR主题探索：从主题出发探索知识网络
        
        Args:
            topic: 起始主题
            depth: 探索深度
        
        Returns:
            dict: 探索结果
        """

    def perception_stats(self, period: str = "summary") -> dict:
        """
        感知命中率统计
        
        Args:
            period: 统计类型（summary/daily）
        
        Returns:
            dict: 统计结果
        """
        if period == "daily":
            return {
                "daily_stats": self.perception_stats_monitor.get_daily_stats(7),
            }
        else:
            return self.perception_stats_monitor.get_summary()
    
    def analyze_text(self, text: str) -> dict:
        """
        LLM文本分析（调用DeepSeek）
        
        Args:
            text: 待分析的文本
        
        Returns:
            dict: 分析结果
        """
        return self.reasoning.analyze(text)
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        LLM文章总结（调用DeepSeek）
        
        Args:
            text: 待总结的文本
            max_length: 最大长度
        
        Returns:
            str: 总结结果
        """
        return self.reasoning.summarize(text, max_length)
    
    def extract_insights(self, text: str) -> dict:
        """
        LLM洞察提取（调用DeepSeek）
        
        Args:
            text: 待分析的文本
        
        Returns:
            dict: 洞察结果
        """
        return self.reasoning.extract_insights(text)
    
    def rules(self, chapter: str = "all") -> dict:
        """
        台律规则查询（按章节返回核心规则）
        
        Args:
            chapter: 章节（all/身份/字段/格式/约束/索引/提炼/体检）
        
        Returns:
            dict: 规则内容
        """
        return self.rules_engine.get_rules(chapter)

    def memory_push(self, key: str, value: str, category: str = "general", source: str = "mcp") -> dict:
        """
        推送记忆到用户画像（即时生效，其他agent可读）

        Args:
            key: 记忆键（如"偏好_回复风格"、"习惯_工作时间"）
            value: 记忆值
            category: 类别（preference/habit/fact/feature）
            source: 来源标识

        Returns:
            dict: 推送结果
        """
        return self.user_profile.push(key, value, category, source)

    def memory_push_batch(self, items: list) -> dict:
        """
        批量推送记忆

        Args:
            items: [{"key": "...", "value": "...", "category": "..."}]

        Returns:
            dict: 批量推送结果
        """
        return self.user_profile.push_batch(items)

    def memory_get_pushes(self, category: str = None) -> dict:
        """
        获取推送的记忆

        Args:
            category: 按类别筛选（可选）

        Returns:
            dict: 推送记忆列表
        """
        pushes = self.user_profile.get_pushes(category)
        return {"pushes": pushes, "count": len(pushes)}

    def recommend_resources(self, topic: str = None) -> dict:
        """
        知识缺口推荐：检测缺口 + Tavily搜索外部资源

        Args:
            topic: 指定主题（可选，默认反思引擎全量扫描）

        Returns:
            dict: 缺口列表 + 外部资源推荐
        """
        # 1. 检测知识缺口
        if topic:
            reflect_result = self.observation_engine.reflect_topic(topic) if hasattr(self.observation_engine, 'reflect_topic') else {"findings": []}
        else:
            reflect_result = {"findings": []}

        # 2. 从原料中提取未提炼的主题
        raw_dir = os.path.join(VAULT_PATH, "原料")
        pending_topics = []
        if os.path.isdir(raw_dir):
            for f in os.listdir(raw_dir):
                if f.endswith('.md'):
                    path = os.path.join(raw_dir, f)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                            content = fp.read(200)
                        if '处理状态: 待提炼' in content:
                            pending_topics.append(f.replace('.md', ''))
                    except Exception:
                        pass

        # 3. 选取前3个待提炼主题，用Tavily搜索推荐
        recommendations = []
        search_topics = pending_topics[:3] if pending_topics else []
        if topic:
            search_topics = [topic]

        for t in search_topics:
            tavily_result = self.tavily_search(t, max_results=3)
            results = tavily_result.get("results", [])
            recommendations.append({
                "topic": t,
                "external_resources": [{"title": r.get("title", ""), "url": r.get("url", "")} for r in results],
            })

        return {
            "pending_count": len(pending_topics),
            "pending_topics": pending_topics[:10],
            "recommendations": recommendations,
        }

    def check_status(self) -> dict:
        """
        检查外部变更状态（git status + 最近10条操作日志）
        多AI协作前调用，确认无外部修改。
        """
        import subprocess
        vault = VAULT_PATH
        repo = os.path.dirname(vault)  # edrc/
        
        # git status
        result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True, text=True, cwd=repo, encoding='utf-8', errors='ignore'
        )
        dirty = result.stdout.strip()
        
        # 最近操作日志
        log_path = os.path.join(vault, '丹房', '日志.md')
        recent_ops = []
        if os.path.isfile(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in reversed(lines[-30:]):
                line = line.strip()
                if line.startswith('['):
                    recent_ops.append(line)
                    if len(recent_ops) >= 10:
                        break
        
        return {
            "has_changes": bool(dirty),
            "changes": dirty.split('\n') if dirty else [],
            "recent_operations": recent_ops,
            "tip": "有外部变更时先 `git pull` 或确认变更来源后再操作"
        }

    # ── skillopt 工具 ─────────────────────────────────────

    def skillopt_dryrun(self) -> dict:
        """预览本轮进化会产出什么。不暂存不改动。"""
        summary = self.skillopt_engine.dry_run()
        return {"type": "dry_run", "summary": summary}

    def skillopt_run(self) -> dict:
        """手动触发进化轮次（不等 03:00）。"""
        summary = self.skillopt_engine.run()
        return {"type": "full_run", "summary": summary}

    def skillopt_status(self) -> dict:
        """查看 staged 规则列表（按自信降序）。"""
        rules = self.skillopt_stager.read()
        return {"type": "status", "staged_count": len(rules), "rules": rules}

    def skillopt_adopt(self, ids: str = "") -> dict:
        """采纳 staged 规则。ids 为空时采纳全部 🟢。"""
        # TODO: 实现真正的 adopt 逻辑（备份感知规则.md → 写入规则）
        return {"type": "adopt", "ids": ids, "status": "not_implemented"}

    def skillopt_reject(self, id: str, reason: str = "") -> dict:
        """拒绝规则 → 记录 blacklist。"""
        # TODO: 实现拒绝写入 blacklist 逻辑
        return {"type": "reject", "id": id, "reason": reason, "status": "not_implemented"}

    def skillopt_log(self, days: int = 7) -> dict:
        """查询进化历史。"""
        # TODO: 读取 changelog.md 并过滤日期范围
        return {"type": "log", "days": days, "status": "not_implemented"}


# MCP 工具定义
TOOLS = [
    {
        "name": "query",
        "description": "查询灵台知识库，支持关键词搜索和图扩散",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "category": {
                    "type": "string",
                    "description": "域分类筛选（如 00-思考与认知，可选）",
                    "default": ""
                },
                "hops": {
                    "type": "integer",
                    "description": "图扩散跳数（默认2）",
                    "default": 2
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "search",
        "description": "搜索页面内容（标题、摘要、正文）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "search_content": {
                    "type": "boolean",
                    "description": "是否搜索页面正文（较慢）",
                    "default": False
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "analyze",
        "description": "分析页面的链接关系和潜在关联",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_path": {
                    "type": "string",
                    "description": "页面路径（如 丹房/00-思考与认知/含人量）"
                }
            },
            "required": ["page_path"]
        }
    },
    {
        "name": "related",
        "description": "获取页面的相关页面",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_path": {
                    "type": "string",
                    "description": "页面路径"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回数",
                    "default": 10
                }
            },
            "required": ["page_path"]
        }
    },
    {
        "name": "stats",
        "description": "获取知识库统计信息",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "domains",
        "description": "获取知识库的域列表",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "pages",
        "description": "获取页面列表",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "域名（可选）"
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回数",
                    "default": 50
                }
            }
        }
    },
    {
        "name": "inject",
        "description": "注入相关知识到回复（AI调用）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "save",
        "description": "保存新知识到原料目录（AI调用）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "知识内容"
                },
                "category": {
                    "type": "string",
                    "description": "分类（可选）",
                    "default": ""
                },
                "source": {
                    "type": "string",
                    "description": "来源",
                    "default": "对话"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "observations",
        "description": "查询自动归纳出的观察（规则⑥）。从观察引擎检索已归纳的知识模式",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词（可选，空则返回全部）",
                    "default": ""
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回数",
                    "default": 20
                }
            }
        }
    },
    {
        "name": "observation_stats",
        "description": "观察层统计信息，查看已归纳的观察总数和置信度",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "hebbian_stats",
        "description": "Hebbian 动态权重统计，查看共现边的权重分布和衰减状态",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "sentinel",
        "description": "感知规则监控报告（Sentinel）。检查各规则的命中率/执行率/健康状态，发现潜在违规",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "tavily_search",
        "description": "联网搜索（Tavily API）。灵库检索无结果时获取外部信息，每日上限1000次",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数（默认5，最大10）",
                    "default": 5
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "profile",
        "description": "获取用户画像（认知偏好+决策风格），让 AI 快速了解用户",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "memory_push",
        "description": "推送记忆到用户画像（即时生效，其他agent可读）。写偏好/习惯/特征，不写知识",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "记忆键，如 '偏好_回复风格'、'习惯_工作时间'"
                },
                "value": {
                    "type": "string",
                    "description": "记忆值"
                },
                "category": {
                    "type": "string",
                    "description": "类别：preference/habit/fact/feature",
                    "default": "general"
                }
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "memory_get_pushes",
        "description": "获取已推送的记忆列表",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "按类别筛选（可选）"
                }
            }
        }
    },
    {
        "name": "recommend_resources",
        "description": "知识缺口推荐：检测未提炼原料 + Tavily搜索外部资源补全方向",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "指定主题（可选，默认扫描全部待提炼原料）"
                }
            }
        }
    },
    {
        "name": "recommend",
        "description": "推荐相关页面（AI调用）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_topic": {
                    "type": "string",
                    "description": "当前话题"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数",
                    "default": 5
                }
            },
            "required": ["current_topic"]
        }
    },
    {
        "name": "context",
        "description": "生成会话上下文摘要（AI调用）",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "graph",
        "description": "从某页面出发的图扩散（支持加权，核心页面权重更高）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_path": {
                    "type": "string",
                    "description": "起始页面路径"
                },
                "hops": {
                    "type": "integer",
                    "description": "扩散跳数（默认3，最大3）",
                    "default": 3
                },
                "weighted": {
                    "type": "boolean",
                    "description": "是否启用加权扩散（默认开启，核心页面权重更高）",
                    "default": True
                }
            },
            "required": ["page_path"]
        }
    },
    {
        "name": "search_logs",
        "description": "搜索日志和体检记录（规则⑤第三步）。从丹房/日志.md和体检/目录按关键词匹配",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "days": {
                    "type": "integer",
                    "description": "回溯天数（默认7天）",
                    "default": 7
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "token",
        "description": "查询 Token 消耗统计",
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "时间段（today/week/month/all）",
                    "default": "today",
                    "enum": ["today", "week", "month", "all"]
                }
            }
        }
    },
    {
        "name": "unified_query",
        "description": "KAR统一查询：知识+关联+推理（一次查询返回完整结果）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "category": {
                    "type": "string",
                    "description": "域分类筛选（如 00-思考与认知，可选）",
                    "default": ""
                },
                "hops": {
                    "type": "integer",
                    "description": "图扩散跳数（默认2）",
                    "default": 2
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "chain_query",
        "description": "KAR链式查询：多关键词串联，发现跨概念关联",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键词列表"
                },
                "hops": {
                    "type": "integer",
                    "description": "每步图扩散跳数（默认2）",
                    "default": 2
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "explore_topic",
        "description": "KAR主题探索：从主题出发探索整个知识网络",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "起始主题"
                },
                "depth": {
                    "type": "integer",
                    "description": "探索深度（默认2）",
                    "default": 2
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "perception_stats",
        "description": "感知命中率统计（规则1-5触发频率和准确率）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "统计类型（summary/daily）",
                    "default": "summary",
                    "enum": ["summary", "daily"]
                }
            }
        }
    },
    {
        "name": "analyze_text",
        "description": "LLM文本分析（调用DeepSeek，返回关键词、分类、情感等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待分析的文本"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "summarize_text",
        "description": "LLM文章总结（调用DeepSeek）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待总结的文本"
                },
                "max_length": {
                    "type": "integer",
                    "description": "最大长度",
                    "default": 200
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "extract_insights",
        "description": "LLM洞察提取（调用DeepSeek，返回核心洞察、启示、行动项）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待分析的文本"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "rules",
        "description": "台律规则查询（按章节返回核心规则：字段格式/链接规范/品级规则等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter": {
                    "type": "string",
                    "description": "章节（all/身份/字段/格式/约束/索引/提炼/体检）",
                    "default": "all",
                    "enum": ["all", "身份", "字段", "格式", "约束", "索引", "提炼", "体检"]
                }
            }
        }
    },
    {
        "name": "reload",
        "description": "热重载灵识模块（代码修改后调用，无需重启MCP Server）",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "check_status",
        "description": "外部变更检查（git status + 最近操作日志）。多AI协作前调用，确认仓库状态",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "skillopt_dryrun",
        "description": "预览 skillopt 进化轮次会产出什么，不暂存不改动",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "skillopt_run",
        "description": "手动触发 skillopt 进化轮次（不等 03:00 调度）",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "skillopt_status",
        "description": "查看 staged 规则列表（按自信降序）",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "skillopt_adopt",
        "description": "采纳 staged 规则。ids 为空时采纳全部 🟢 推荐",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "string",
                    "description": "逗号分隔的规则ID列表（可选，空=采纳全部推荐）",
                    "default": ""
                }
            }
        }
    },
    {
        "name": "skillopt_reject",
        "description": "拒绝规则并记录到 blacklist，避免重复生成",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "规则ID（如 R01）"
                },
                "reason": {
                    "type": "string",
                    "description": "拒绝原因（可选）",
                    "default": ""
                }
            },
            "required": ["id"]
        }
    },
    {
        "name": "skillopt_log",
        "description": "查看 skillopt 进化历史日志",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "回溯天数（默认7）",
                    "default": 7
                }
            }
        }
    }
]


# 全局服务器实例
server = LingtaiMCPServer()


def handle_request(request: dict) -> dict:
    """处理 MCP 请求"""
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "lingtai-knowledge-base",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "query":
                result = server.query(**arguments)
            elif tool_name == "search":
                result = server.search(**arguments)
            elif tool_name == "analyze":
                result = server.analyze(**arguments)
            elif tool_name == "related":
                result = server.related(**arguments)
            elif tool_name == "stats":
                result = server.stats()
            elif tool_name == "domains":
                result = server.domains()
            elif tool_name == "pages":
                result = server.pages(**arguments)
            elif tool_name == "inject":
                result = server.inject(**arguments)
            elif tool_name == "save":
                result = server.save(**arguments)
            elif tool_name == "observations":
                result = server.observations(**arguments)
            elif tool_name == "observation_stats":
                result = server.observation_stats()
            elif tool_name == "hebbian_stats":
                result = server.hebbian_stats()
            elif tool_name == "sentinel":
                result = server.sentinel()
            elif tool_name == "tavily_search":
                result = server.tavily_search(**arguments)
            elif tool_name == "profile":
                result = server.profile()
            elif tool_name == "memory_push":
                result = server.memory_push(**arguments)
            elif tool_name == "memory_get_pushes":
                result = server.memory_get_pushes(**arguments)
            elif tool_name == "recommend_resources":
                result = server.recommend_resources(**arguments)
            elif tool_name == "recommend":
                result = server.recommend(**arguments)
            elif tool_name == "context":
                result = server.context()
            elif tool_name == "graph":
                result = server.graph(**arguments)
            elif tool_name == "search_logs":
                result = server.search_logs(**arguments)
            elif tool_name == "token":
                result = server.token(**arguments)
            elif tool_name == "unified_query":
                result = server.unified_query(**arguments)
            elif tool_name == "chain_query":
                result = server.chain_query(**arguments)
            elif tool_name == "explore_topic":
                result = server.explore_topic(**arguments)
            elif tool_name == "perception_stats":
                result = server.perception_stats(**arguments)
            elif tool_name == "analyze_text":
                result = server.analyze_text(**arguments)
            elif tool_name == "summarize_text":
                result = server.summarize_text(**arguments)
            elif tool_name == "extract_insights":
                result = server.extract_insights(**arguments)
            elif tool_name == "rules":
                result = server.rules(**arguments)
            elif tool_name == "reload":
                result = server.reload()
            elif tool_name == "check_status":
                result = server.check_status()
            elif tool_name == "skillopt_dryrun":
                result = server.skillopt_dryrun()
            elif tool_name == "skillopt_run":
                result = server.skillopt_run()
            elif tool_name == "skillopt_status":
                result = server.skillopt_status()
            elif tool_name == "skillopt_adopt":
                result = server.skillopt_adopt(**arguments)
            elif tool_name == "skillopt_reject":
                result = server.skillopt_reject(**arguments)
            elif tool_name == "skillopt_log":
                result = server.skillopt_log(**arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method: {method}"
            }
        }


def main():
    """主函数 - 通过 stdin/stdout 通信"""
    # Windows GBK 环境下强制 UTF-8 输出，防止中文乱码
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            print(json.dumps(error_response, ensure_ascii=False))
            sys.stdout.flush()


if __name__ == "__main__":
    # 测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("灵台知识库 MCP Server 测试")
        print("=" * 50)
        
        # 测试 stats
        result = server.stats()
        print(f"\n📊 知识库统计:")
        print(f"  总页面: {result['total_pages']}")
        print(f"  总链接: {result['total_links']}")
        print(f"  核心页面: {result['core_pages']}")
        
        # 测试 query
        result = server.query("AI")
        print(f"\n🔍 查询 'AI':")
        print(f"  直接匹配: {result['direct_matches']}")
        print(f"  关联知识: {result['related_knowledge']}")
        
        # 测试 domains
        result = server.domains()
        print(f"\n📁 域列表 ({result['total']} 个):")
        for d in result['domains'][:5]:
            print(f"  - {d['name']}: {d['count']} 页")
        
        print("\n✅ 测试完成")
    else:
        # MCP 模式
        main()
