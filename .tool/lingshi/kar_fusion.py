# -*- coding: utf-8 -*-
"""
灵台灵识 - KAR融合模块
====================
Knowledge-Association-Reasoning 统一管线。

功能：
1. 统一查询：一次查询，同时返回知识+关联+推理结果
2. 关联增强：利用自动建边结果增强图扩散
3. 推理增强：利用关联信息增强推理深度
4. 智能推荐：基于知识图谱推荐相关页面

设计原则：
- 零额外API成本
- 复用现有模块（memory_engine, auto_edge, reasoning_engine）
- 统一入口，简化调用
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_engine import MemoryEngine
from auto_edge import AutoEdge


class KARFusion:
    """灵台灵识 KAR融合引擎"""
    
    def __init__(self, vault_path: str = None):
        """
        初始化KAR融合引擎
        
        Args:
            vault_path: 灵台vault路径
        """
        if vault_path is None:
            self.vault_path = r"os.environ.get("LINGTAI_VAULT", "")"
        else:
            self.vault_path = vault_path
        
        self.memory = MemoryEngine(self.vault_path)
        self.auto_edge = AutoEdge(self.vault_path)
    
    def unified_query(self, keyword: str, hops: int = 2, include_reasoning: bool = True) -> dict:
        """
        统一查询：一次查询，同时返回知识+关联+推理结果
        
        Args:
            keyword: 搜索关键词
            hops: 图扩散跳数
            include_reasoning: 是否包含推理分析
        
        Returns:
            dict: 统一查询结果
        """
        start_time = datetime.now()
        
        # 1. 知识检索(K)
        direct_results = self.memory.query(keyword)
        
        # 2. 关联发现(A) - 利用图扩散
        graph_results = self.memory.search_graph(keyword, hops=hops)
        
        # 3. 推理增强(R) - 基于关联信息
        reasoning_result = {}
        if include_reasoning and direct_results:
            reasoning_result = self._enhance_reasoning(keyword, direct_results, graph_results)
        
        # 4. 智能推荐
        recommendations = self._smart_recommend(keyword, direct_results, graph_results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return {
            "keyword": keyword,
            "hops": hops,
            "knowledge": {
                "direct_matches": len(direct_results),
                "results": [
                    {
                        "path": p["path"],
                        "title": p["title"],
                        "summary": p.get("summary", "")[:150],
                        "domain": p.get("domain", ""),
                        "tags": p.get("tags", []),
                    }
                    for p in direct_results[:10]
                ],
            },
            "association": {
                "graph_matches": len(graph_results),
                "results": [
                    {
                        "path": p["path"],
                        "title": p["title"],
                        "summary": p.get("summary", "")[:100],
                        "hop": self._get_hop_distance(keyword, p, graph_results),
                    }
                    for p in graph_results[:15]
                ],
            },
            "reasoning": reasoning_result,
            "recommendations": recommendations,
            "elapsed_seconds": round(elapsed, 3),
        }
    
    def _enhance_reasoning(self, keyword: str, direct_results: list, graph_results: list) -> dict:
        """
        基于关联信息增强推理
        
        Args:
            keyword: 搜索关键词
            direct_results: 直接匹配结果
            graph_results: 图扩散结果
        
        Returns:
            dict: 推理结果
        """
        # 收集所有相关页面的摘要
        all_summaries = []
        for p in direct_results[:5]:
            if p.get("summary"):
                all_summaries.append(p["summary"])
        for p in graph_results[:5]:
            if p.get("summary"):
                all_summaries.append(p["summary"])
        
        if not all_summaries:
            return {"insight": "", "connections": []}
        
        # 分析连接关系
        connections = []
        
        # 找到共同主题
        common_tags = set()
        for p in direct_results + graph_results:
            common_tags.update(p.get("tags", []))
        
        # 找到跨域连接
        domains = set()
        for p in direct_results + graph_results:
            domain = p.get("domain", "")
            if domain:
                domains.add(domain)
        
        cross_domain = len(domains) > 1
        
        # 生成洞察
        insight_parts = []
        if len(direct_results) > 1:
            insight_parts.append(f"找到 {len(direct_results)} 个直接相关页面")
        if len(graph_results) > len(direct_results):
            insight_parts.append(f"通过 {len(graph_results) - len(direct_results)} 个关联页面扩展了搜索范围")
        if cross_domain:
            insight_parts.append(f"跨越 {len(domains)} 个知识域")
        if common_tags:
            insight_parts.append(f"共同标签: {', '.join(list(common_tags)[:3])}")
        
        return {
            "insight": "；".join(insight_parts) if insight_parts else "未发现明显关联模式",
            "connections": connections,
            "cross_domain": cross_domain,
            "domains": list(domains),
            "common_tags": list(common_tags)[:5],
        }
    
    def _smart_recommend(self, keyword: str, direct_results: list, graph_results: list) -> list:
        """
        智能推荐：基于知识图谱推荐相关页面
        
        Args:
            keyword: 搜索关键词
            direct_results: 直接匹配结果
            graph_results: 图扩散结果
        
        Returns:
            list: 推荐列表
        """
        # 收集已出现的路径
        seen_paths = set()
        for p in direct_results + graph_results:
            seen_paths.add(p["path"])
        
        # 找到图扩散中未直接匹配但高度相关的页面
        recommendations = []
        for p in graph_results:
            if p["path"] not in [r["path"] for r in direct_results]:
                recommendations.append({
                    "path": p["path"],
                    "title": p["title"],
                    "reason": "通过知识图谱关联发现",
                })
        
        return recommendations[:5]
    
    def _get_hop_distance(self, keyword: str, page: dict, graph_results: list) -> int:
        """获取页面的跳数距离"""
        # 简化实现：直接匹配为0跳，图扩散为1+跳
        for p in graph_results:
            if p["path"] == page["path"]:
                return 1
        return 2
    
    def chain_query(self, keywords: list, hops: int = 2) -> dict:
        """
        链式查询：多个关键词串联查询，发现跨概念关联
        
        Args:
            keywords: 关键词列表
            hops: 每步图扩散跳数
        
        Returns:
            dict: 链式查询结果
        """
        all_results = []
        connections = []
        
        # 对每个关键词进行查询
        for i, keyword in enumerate(keywords):
            result = self.unified_query(keyword, hops=hops, include_reasoning=False)
            all_results.append(result)
        
        # 发现跨关键词关联
        seen_paths = set()
        for result in all_results:
            for p in result["knowledge"]["results"]:
                if p["path"] not in seen_paths:
                    seen_paths.add(p["path"])
                    connections.append({
                        "path": p["path"],
                        "title": p["title"],
                        "found_in": "直接匹配",
                    })
            for p in result["association"]["results"]:
                if p["path"] not in seen_paths:
                    seen_paths.add(p["path"])
                    connections.append({
                        "path": p["path"],
                        "title": p["title"],
                        "found_in": "关联发现",
                    })
        
        # 找到同时被多个关键词命中的页面
        cross_hits = []
        path_counts = {}
        for result in all_results:
            for p in result["knowledge"]["results"] + result["association"]["results"]:
                path_counts[p["path"]] = path_counts.get(p["path"], 0) + 1
        
        for path, count in path_counts.items():
            if count > 1:
                page_info = next(
                    (p for r in all_results 
                     for p in r["knowledge"]["results"] + r["association"]["results"]
                     if p["path"] == path),
                    None
                )
                if page_info:
                    cross_hits.append({
                        "path": path,
                        "title": page_info["title"],
                        "hit_count": count,
                    })
        
        return {
            "keywords": keywords,
            "total_results": len(connections),
            "cross_hits": cross_hits,
            "connections": connections[:20],
        }
    
    def explore_topic(self, topic: str, depth: int = 2) -> dict:
        """
        主题探索：从一个主题出发，探索整个知识网络
        
        Args:
            topic: 起始主题
            depth: 探索深度
        
        Returns:
            dict: 探索结果
        """
        # 获取起始页面
        start_pages = self.memory.query(topic)
        
        if not start_pages:
            return {"topic": topic, "found": False}
        
        # BFS探索
        visited = set()
        explored = []
        queue = [(p, 0) for p in start_pages[:3]]  # 从3个起始点开始
        
        while queue:
            current_page, current_depth = queue.pop(0)
            
            if current_page["path"] in visited:
                continue
            if current_depth > depth:
                continue
            
            visited.add(current_page["path"])
            explored.append({
                "path": current_page["path"],
                "title": current_page["title"],
                "depth": current_depth,
                "domain": current_page.get("domain", ""),
                "tags": current_page.get("tags", []),
            })
            
            # 找到关联页面
            for link in current_page.get("links_to", []):
                neighbor = self.memory.get_page_by_path(link)
                if neighbor and neighbor["path"] not in visited:
                    queue.append((neighbor, current_depth + 1))
            
            for link in current_page.get("linked_from", []):
                neighbor = self.memory.get_page_by_path(link)
                if neighbor and neighbor["path"] not in visited:
                    queue.append((neighbor, current_depth + 1))
        
        # 分析探索结果
        domains = {}
        all_tags = set()
        for p in explored:
            domain = p.get("domain", "")
            if domain:
                domains[domain] = domains.get(domain, 0) + 1
            all_tags.update(p.get("tags", []))
        
        return {
            "topic": topic,
            "found": True,
            "depth": depth,
            "explored_count": len(explored),
            "domains": domains,
            "tags": list(all_tags)[:10],
            "pages": explored[:20],
        }


# 便捷函数
def create_kar_fusion(vault_path: str = None) -> KARFusion:
    """创建KAR融合实例"""
    return KARFusion(vault_path)


if __name__ == "__main__":
    # 测试
    kar = KARFusion()
    
    print("KAR融合测试")
    print("=" * 50)
    
    # 测试统一查询
    print("\n统一查询 'O与π':")
    result = kar.unified_query("O与π", hops=2)
    print(f"  知识匹配: {result['knowledge']['direct_matches']}")
    print(f"  关联匹配: {result['association']['graph_matches']}")
    print(f"  跨域: {result['reasoning'].get('cross_domain', False)}")
    print(f"  耗时: {result['elapsed_seconds']}s")
    
    # 测试链式查询
    print("\n链式查询 ['O与π', '含人量']:")
    result = kar.chain_query(["O与π", "含人量"])
    print(f"  总结果: {result['total_results']}")
    print(f"  交叉命中: {len(result['cross_hits'])}")
    
    # 测试主题探索
    print("\n主题探索 '追问':")
    result = kar.explore_topic("追问", depth=2)
    print(f"  探索页面: {result['explored_count']}")
    print(f"  涉及域: {result['domains']}")
    
    print("\n✅ 测试完成")
