# -*- coding: utf-8 -*-
"""
灵台灵识 - 记忆引擎模块 V2
===========================
基于灵台 index.json 的记忆引擎，替代原有的独立数据库。

功能：
- 从 index.json 读取知识图谱
- 图扩散搜索（利用 linked_from 和 links_to）
- 智能查询
- 统计分析
- 缓存预热
- 并发查询
"""

import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from hebbian_weights import HebbianWeights


class MemoryEngine:
    """灵台灵识记忆引擎 V2 - 基于 index.json"""
    
    def __init__(self, vault_path: str = None):
        """
        初始化记忆引擎
        
        Args:
            vault_path: 灵台vault路径
        """
        if vault_path is None:
            self.vault_path = r"os.environ.get("LINGTAI_VAULT", "")"
        else:
            self.vault_path = vault_path
        
        # index.json 路径
        self.index_path = os.path.join(self.vault_path, "丹房", ".meta", "index.json")
        
        # 缓存目录
        self.cache_dir = Path(__file__).parent / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # 内存缓存
        self._query_cache = {}
        self._cache_ttl = 3600  # 1小时过期
        
        # 加载数据
        self.data = self._load_index()
        self.pages = self.data.get("pages", [])
        
        # 构建快速查找映射
        self._build_maps()
        
        # 加载持久化缓存
        self._load_persistent_cache()
        
        # Hebbian 动态权重
        self.hebbian = HebbianWeights(self.vault_path)
    
    def _load_index(self) -> dict:
        """加载 index.json"""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️ 加载 index.json 失败: {e}")
        
        return {"pages": [], "_stats": {}}
    
    def _build_maps(self):
        """构建快速查找映射"""
        # path -> page
        self.path_map = {p["path"]: p for p in self.pages}
        
        # filename -> page
        self.name_map = {p["filename"]: p for p in self.pages}
        
        # tag -> [pages]
        self.tag_map = {}
        for p in self.pages:
            for tag in p.get("tags", []):
                if tag not in self.tag_map:
                    self.tag_map[tag] = []
                self.tag_map[tag].append(p)
        
        # domain -> [pages]
        self.domain_map = {}
        for p in self.pages:
            domain = p.get("domain", "")
            if domain:
                if domain not in self.domain_map:
                    self.domain_map[domain] = []
                self.domain_map[domain].append(p)
    
    # ==================== 持久化缓存 ====================
    
    def _get_cache_key(self, text: str, operation: str) -> str:
        """生成缓存键"""
        content = f"{operation}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_persistent_cache(self):
        """加载持久化缓存"""
        cache_file = self.cache_dir / "query_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self._query_cache = json.load(f)
            except Exception:
                self._query_cache = {}
    
    def _save_persistent_cache(self):
        """保存持久化缓存"""
        cache_file = self.cache_dir / "query_cache.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self._query_cache, f, ensure_ascii=False)
        except Exception:
            pass
    
    def _get_cached(self, cache_key: str) -> Optional[dict]:
        """获取缓存"""
        cached = self._query_cache.get(cache_key)
        if cached:
            # 检查是否过期
            if datetime.now().timestamp() - cached.get("timestamp", 0) < self._cache_ttl:
                return cached.get("result")
        return None
    
    def _set_cached(self, cache_key: str, result: dict):
        """设置缓存"""
        self._query_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now().timestamp()
        }
        # 定期保存（每10次操作）
        if len(self._query_cache) % 10 == 0:
            self._save_persistent_cache()
    
    def clear_cache(self):
        """清空缓存"""
        self._query_cache = {}
        cache_file = self.cache_dir / "query_cache.json"
        if cache_file.exists():
            cache_file.unlink()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        cache_file = self.cache_dir / "query_cache.json"
        cache_size = 0
        if cache_file.exists():
            cache_size = cache_file.stat().st_size
        
        return {
            "memory_entries": len(self._query_cache),
            "disk_size": cache_size,
            "cache_dir": str(self.cache_dir),
        }
    
    def refresh(self):
        """刷新数据（重新加载 index.json）"""
        self.data = self._load_index()
        self.pages = self.data.get("pages", [])
        self._build_maps()
    
    # ==================== 缓存预热 ====================
    
    def warmup_cache(self, keywords: List[str] = None):
        """
        缓存预热：预加载常用查询结果
        
        Args:
            keywords: 要预热的关键词列表（默认：高频页面标题）
        """
        if keywords is None:
            # 预热高频页面
            keywords = []
            for p in self.pages[:20]:  # 前20个页面
                title = p.get("title", "")
                if title:
                    keywords.append(title)
        
        # 预热查询
        for keyword in keywords[:10]:  # 限制10个
            self.query(keyword, use_ngram_fallback=False)
    
    def get_page_stats(self) -> dict:
        """获取页面统计（用于缓存预热决策）"""
        return {
            "total_pages": len(self.pages),
            "total_links": sum(len(p.get("links_to", [])) for p in self.pages),
            "core_pages": sum(1 for p in self.pages if p.get("is_core")),
            "hub_pages": sorted(
                [(p["title"], len(p.get("linked_from", []))) for p in self.pages],
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }
    
    # ==================== 并发查询 ====================
    
    def parallel_query(self, keywords: List[str], max_workers: int = 4) -> Dict[str, dict]:
        """
        并发查询多个关键词
        
        Args:
            keywords: 关键词列表
            max_workers: 最大并发数
        
        Returns:
            dict: 关键词到结果的映射
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有查询任务
            future_to_keyword = {
                executor.submit(self.query, keyword): keyword
                for keyword in keywords
            }
            
            # 收集结果
            for future in as_completed(future_to_keyword):
                keyword = future_to_keyword[future]
                try:
                    result = future.result()
                    results[keyword] = result
                except Exception as e:
                    results[keyword] = {"error": str(e)}
        
        return results
    
    def parallel_search_graph(self, keywords: List[str], hops: int = 3, max_workers: int = 4) -> Dict[str, list]:
        """
        并发图扩散搜索
        
        Args:
            keywords: 关键词列表
            hops: 扩散跳数
            max_workers: 最大并发数
        
        Returns:
            dict: 关键词到结果的映射
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有搜索任务
            future_to_keyword = {
                executor.submit(self.search_graph, keyword, hops): keyword
                for keyword in keywords
            }
            
            # 收集结果
            for future in as_completed(future_to_keyword):
                keyword = future_to_keyword[future]
                try:
                    result = future.result()
                    results[keyword] = result
                except Exception as e:
                    results[keyword] = []
        
        return results
    
    def query(self, keyword: str, use_ngram_fallback: bool = True) -> dict:
        """
        查询知识（支持n-gram回退 + 缓存）
        
        Args:
            keyword: 搜索关键词
            use_ngram_fallback: 是否启用n-gram回退
        
        Returns:
            dict: 查询结果，包含匹配类型
        """
        # 检查缓存
        cache_key = self._get_cache_key(keyword, "query")
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # 第一步：精确匹配
        exact_results = self._exact_match(keyword)
        
        if exact_results:
            result = {
                "results": exact_results,
                "match_type": "exact",
                "keyword": keyword,
            }
            self._set_cached(cache_key, result)
            return result
        
        # 第二步：n-gram回退（如果启用）
        if use_ngram_fallback:
            ngram_results = self._ngram_match(keyword)
            
            if ngram_results:
                result = {
                    "results": ngram_results,
                    "match_type": "ngram",
                    "keyword": keyword,
                    "ngrams": self._generate_ngrams(keyword),
                }
                self._set_cached(cache_key, result)
                return result
        
        # 无结果
        result = {
            "results": [],
            "match_type": "none",
            "keyword": keyword,
        }
        self._set_cached(cache_key, result)
        return result
    
    def _exact_match(self, keyword: str) -> list:
        """精确匹配"""
        results = []
        keyword_lower = keyword.lower()
        
        for page in self.pages:
            # 检查标题
            title = page.get("title", "").lower()
            if keyword_lower in title:
                results.append(page)
                continue
            
            # 检查摘要
            summary = page.get("summary", "").lower()
            if keyword_lower in summary:
                results.append(page)
                continue
            
            # 检查标签
            tags = page.get("tags", [])
            for tag in tags:
                if keyword_lower in tag.lower():
                    results.append(page)
                    break
        
        return results
    
    def _generate_ngrams(self, text: str, n: int = 3) -> list:
        """生成字符级n-gram"""
        ngrams = []
        text = text.lower()
        
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            if ngram.strip():  # 忽略纯空格n-gram
                ngrams.append(ngram)
        
        return ngrams
    
    def _ngram_match(self, keyword: str, n: int = 3) -> list:
        """
        n-gram模糊匹配
        
        Args:
            keyword: 搜索关键词
            n: n-gram长度
        
        Returns:
            list: 匹配的页面列表
        """
        # 生成关键词的n-gram
        keyword_ngrams = set(self._generate_ngrams(keyword, n))
        
        if not keyword_ngrams:
            return []
        
        results = []
        seen_paths = set()
        
        for page in self.pages:
            if page["path"] in seen_paths:
                continue
            
            # 构建页面文本的n-gram
            page_text = (
                page.get("title", "") + " " +
                page.get("summary", "") + " " +
                " ".join(page.get("tags", []))
            ).lower()
            
            page_ngrams = set(self._generate_ngrams(page_text, n))
            
            # 计算n-gram重叠率
            if not page_ngrams:
                continue
            
            overlap = len(keyword_ngrams & page_ngrams)
            overlap_ratio = overlap / len(keyword_ngrams)
            
            # 如果重叠率超过阈值，认为匹配
            if overlap_ratio >= 0.3:
                seen_paths.add(page["path"])
                results.append(page)
        
        return results
    
    def search_graph(self, keyword: str, hops: int = 3, weighted: bool = True) -> list:
        """
        图扩散搜索（支持加权扩散）
        
        Args:
            keyword: 起始关键词
            hops: 扩散跳数（默认3，最大3）
            weighted: 是否启用加权扩散（默认开启，核心页面权重更高）
        
        Returns:
            list: 关联的页面列表（按权重排序）
        """
        # 限制最大跳数
        hops = min(hops, 3)
        
        # 先找到匹配的页面
        query_result = self.query(keyword)
        start_pages = query_result.get("results", [])
        
        if not start_pages:
            return []
        
        # BFS扩散（带权重）
        visited = set()
        result_pages = []
        # 队列元素：(页面, 跳数, 权重分数)
        queue = [(page, 0, 1.0) for page in start_pages]
        
        while queue:
            current_page, current_hop, current_weight = queue.pop(0)
            
            page_path = current_page["path"]
            if page_path in visited:
                continue
            if current_hop > hops:
                continue
            
            visited.add(page_path)
            
            # 计算页面权重
            page_weight = self._calculate_page_weight(current_page, start_pages[0]["path"]) if weighted else 1.0
            final_weight = current_weight * page_weight
            
            result_pages.append({
                **current_page,
                "weight": round(final_weight, 3),
                "hop": current_hop,
            })
            
            # 找到关联页面（出链）
            for link in current_page.get("links_to", []):
                if link in self.path_map and link not in visited:
                    queue.append((self.path_map[link], current_hop + 1, final_weight))
            
            # 找到关联页面（入链）
            for link in current_page.get("linked_from", []):
                if link in self.path_map and link not in visited:
                    queue.append((self.path_map[link], current_hop + 1, final_weight))
        
        # 按权重排序（加权模式）
        if weighted:
            result_pages.sort(key=lambda x: x.get("weight", 0), reverse=True)
        
        # 记录边的使用（Hebbian权重）
        for i, page_a in enumerate(result_pages):
            for page_b in result_pages[i+1:]:
                self.hebbian.on_query(page_a["path"], page_b["path"])
        
        return result_pages
    
    def _calculate_page_weight(self, page: dict, query_page: str = None) -> float:
        """
        计算页面权重
        
        权重因素：
        - 核心页面（⚡标记）：权重 ×1.5
        - 高入链页面：权重 ×1.2
        - 最近更新：权重 ×1.1
        - Hebbian 边权重：与查询页面的共现频率
        """
        weight = 1.0
        
        # 核心页面
        if page.get("is_core"):
            weight *= 1.5
        
        # 高入链（>10个入链）
        backlinks = len(page.get("linked_from", []))
        if backlinks > 10:
            weight *= 1.2
        elif backlinks > 5:
            weight *= 1.1
        
        # 最近更新（30天内）
        date_str = page.get("date", "")
        if date_str:
            try:
                page_date = datetime.strptime(date_str, "%Y-%m-%d")
                if (datetime.now() - page_date).days < 30:
                    weight *= 1.1
            except:
                pass
        
        # Hebbian 边权重：从查询页到目标页的共现频率加成
        if query_page:
            hebbian_weight = self.hebbian.get_weight(query_page, page["path"])
            if hebbian_weight > 0.5:  # 只有高于默认权重才加成
                weight *= (1.0 + hebbian_weight * 0.5)  # 最高加成 2.0 倍
        
        return weight
    
    def get_page_by_path(self, path: str) -> Optional[dict]:
        """根据路径获取页面"""
        return self.path_map.get(path)
    
    def get_page_by_name(self, name: str) -> Optional[dict]:
        """根据文件名获取页面"""
        return self.name_map.get(name)
    
    def get_pages_by_tag(self, tag: str) -> list:
        """根据标签获取页面"""
        return self.tag_map.get(tag, [])
    
    def get_pages_by_domain(self, domain: str) -> list:
        """根据域名获取页面"""
        return self.domain_map.get(domain, [])
    
    def get_core_pages(self) -> list:
        """获取核心页面"""
        return [p for p in self.pages if p.get("is_core")]
    
    def get_gate_pages(self) -> list:
        """获取门控页面"""
        return [p for p in self.pages if p.get("is_gate")]
    
    def get_related_pages(self, path: str, max_results: int = 10) -> list:
        """
        获取相关页面（基于链接关系）
        
        Args:
            path: 页面路径
            max_results: 最大结果数
        
        Returns:
            list: 相关页面列表
        """
        page = self.get_page_by_path(path)
        if not page:
            return []
        
        related = set()
        
        # 出链
        for link in page.get("links_to", []):
            if link != path:
                related.add(link)
        
        # 入链
        for link in page.get("linked_from", []):
            if link != path:
                related.add(link)
        
        # 转换为页面对象并限制数量
        result = []
        for link in list(related)[:max_results]:
            if link in self.path_map:
                result.append(self.path_map[link])
        
        return result
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = self.data.get("_stats", {})
        
        # 补充实时统计
        total_links = sum(len(p.get("links_to", [])) for p in self.pages)
        total_backlinks = sum(len(p.get("linked_from", [])) for p in self.pages)
        
        return {
            "total_pages": stats.get("total_pages", len(self.pages)),
            "core_pages": stats.get("core_pages", 0),
            "gate_pages": stats.get("gate_pages", 0),
            "isolated_pages": stats.get("isolated_pages", 0),
            "deadend_pages": stats.get("deadend_pages", 0),
            "total_links": total_links,
            "total_backlinks": total_backlinks,
            "by_domain": stats.get("by_domain", {}),
            "by_pinji": stats.get("by_pinji", {}),
            "by_status": stats.get("by_status", {}),
        }
    
    def search_by_summary(self, keyword: str) -> list:
        """在摘要中搜索"""
        results = []
        keyword_lower = keyword.lower()
        
        for page in self.pages:
            summary = page.get("summary", "").lower()
            if keyword_lower in summary:
                results.append(page)
        
        return results
    
    def search_by_content(self, keyword: str) -> list:
        """
        搜索页面内容（需要读取.md文件）
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            list: 匹配的页面列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        for page in self.pages:
            file_path = os.path.join(self.vault_path, page["path"] + ".md")
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                
                if keyword_lower in content:
                    results.append(page)
            except:
                pass
        
        return results


def create_engine(vault_path: str = None) -> MemoryEngine:
    """创建记忆引擎实例"""
    return MemoryEngine(vault_path)


if __name__ == "__main__":
    # 测试
    engine = MemoryEngine()
    
    # 查询测试
    qr = engine.query("Python")
    results = qr.get("results", [])
    print(f"查询 'Python': {len(results)} 条结果")
    for p in results[:3]:
        print(f"  - {p['title']}: {p['summary'][:50]}...")
    
    # 图扩散测试
    graph_results = engine.search_graph("Python", hops=1)
    print(f"\n图扩散搜索 'Python': {len(graph_results)} 条结果")
    
    # 统计
    stats = engine.get_stats()
    print(f"\n统计: {stats['total_pages']} 页, {stats['total_links']} 链接")
