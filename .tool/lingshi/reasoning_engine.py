# -*- coding: utf-8 -*-
"""
灵台灵识 - 推理引擎模块
======================
基于灵识的推理引擎，适配灵台的Markdown知识管理系统。

功能：
- 文本分析（LLM增强）
- 文章总结（LLM增强）
- 因果链提取
- 洞察提取（LLM增强）
- 链接建议（LLM增强）
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# 尝试导入LLM推理引擎
try:
    from llm_reasoning import LLMReasoning
    HAS_LLM = True
except ImportError:
    try:
        from .llm_reasoning import LLMReasoning
        HAS_LLM = True
    except ImportError:
        HAS_LLM = False


class ReasoningEngine:
    """灵台灵识推理引擎"""
    
    def __init__(self, data_dir: str = None, use_llm: bool = True):
        """
        初始化推理引擎
        
        Args:
            data_dir: 数据目录路径
            use_llm: 是否使用LLM增强
        """
        if data_dir is None:
            skill_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = skill_dir / ".meta"
        
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "left_brain_data.json"
        
        # 初始化LLM推理引擎（如果可用）
        self.llm = None
        if use_llm and HAS_LLM:
            try:
                self.llm = LLMReasoning()
            except Exception:
                pass
        
        # 加载数据
        self.data = self._load_data()
    
    def _load_data(self) -> dict:
        """加载数据文件"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        return {"nodes": [], "edges": [], "stats": {}}
    
    def analyze(self, text: str) -> dict:
        """
        分析文本
        
        Args:
            text: 待分析的文本
        
        Returns:
            dict: 分析结果
        """
        # 优先使用LLM分析
        if self.llm:
            try:
                llm_result = self.llm.analyze(text)
                # 合并基础分析结果
                basic_result = self._basic_analyze(text)
                return {
                    "summary": llm_result.get("summary", ""),
                    "keywords": llm_result.get("keywords", []),
                    "key_sentences": basic_result.get("key_sentences", []),
                    "numbers": basic_result.get("numbers", []),
                    "char_count": basic_result.get("char_count", 0),
                    "sentence_count": basic_result.get("sentence_count", 0),
                    "category": llm_result.get("category", ""),
                    "sentiment": llm_result.get("sentiment", ""),
                    "complexity": llm_result.get("complexity", "")
                }
            except Exception:
                pass
        
        # 回退到基础分析
        return self._basic_analyze(text)
    
    def _basic_analyze(self, text: str) -> dict:
        """基础文本分析（不依赖LLM）"""
        # 提取数字
        numbers = re.findall(r'\d+\.?\d*', text)
        
        # 提取关键句（基于句号、感叹号、问号分割）
        sentences = re.split(r'[。！？\n]', text)
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 5][:5]
        
        # 提取关键词（中英文混合支持）
        word_freq = {}
        current_en = []
        
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                # 中文字符
                if current_en:
                    word = ''.join(current_en)
                    if len(word) >= 2:
                        word_freq[word] = word_freq.get(word, 0) + 1
                    current_en = []
                # 单个中文字符不作为关键词
            elif ch.isalnum():
                current_en.append(ch)
            else:
                if current_en:
                    word = ''.join(current_en)
                    if len(word) >= 2:
                        word_freq[word] = word_freq.get(word, 0) + 1
                    current_en = []
        
        # 处理末尾英文
        if current_en:
            word = ''.join(current_en)
            if len(word) >= 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序，取前10个
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 统计字符数（对中文更准确）
        char_count = len(text)
        
        return {
            "numbers": numbers,
            "key_sentences": key_sentences,
            "keywords": [w[0] for w in top_words],
            "char_count": char_count,
            "sentence_count": len([s for s in sentences if s.strip()])
        }
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """
        总结文本
        
        Args:
            text: 待总结的文本
            max_length: 最大长度
        
        Returns:
            str: 总结结果
        """
        # 优先使用LLM总结
        if self.llm:
            try:
                return self.llm.summarize(text, max_length)
            except Exception:
                pass
        
        # 回退到基础总结：取前几句
        sentences = re.split(r'[。！？]', text)
        summary_sentences = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) > max_length:
                break
            
            summary_sentences.append(sentence)
            current_length += len(sentence)
        
        return "。".join(summary_sentences) + "。" if summary_sentences else text[:max_length]
    
    def entangle(self, keyword: str, hops: int = 2) -> list:
        """
        纠缠场关联分析
        
        Args:
            keyword: 关键词
            hops: 扩散跳数
        
        Returns:
            list: 关联的知识链
        """
        # 找到匹配的节点
        start_nodes = []
        keyword_lower = keyword.lower()
        
        for node in self.data["nodes"]:
            if keyword_lower in node["text"].lower():
                start_nodes.append(node)
        
        if not start_nodes:
            return []
        
        # BFS扩散
        visited = set()
        result_chain = []
        queue = [(node, 0, [node["text"]]) for node in start_nodes]
        
        while queue:
            current_node, current_hop, current_chain = queue.pop(0)
            
            if current_node["id"] in visited:
                continue
            if current_hop > hops:
                continue
            
            visited.add(current_node["id"])
            result_chain.append({
                "node": current_node,
                "chain": current_chain,
                "hop": current_hop
            })
            
            # 找到关联节点
            for edge in self.data["edges"]:
                neighbor_id = None
                if edge["source"] == current_node["id"]:
                    neighbor_id = edge["target"]
                elif edge["target"] == current_node["id"]:
                    neighbor_id = edge["source"]
                
                if neighbor_id and neighbor_id not in visited:
                    neighbor = self._get_node_by_id(neighbor_id)
                    if neighbor:
                        new_chain = current_chain + [neighbor["text"]]
                        queue.append((neighbor, current_hop + 1, new_chain))
        
        return result_chain
    
    def extract_causality(self, text: str) -> list:
        """
        提取因果链
        
        Args:
            text: 待分析的文本
        
        Returns:
            list: 因果链列表
        """
        # 简单的因果关系提取（基于关键词）
        causality_patterns = [
            (r'因为(.+?)所以(.+?)。', '因为{}所以{}'),
            (r'由于(.+?)导致(.+?)。', '由于{}导致{}'),
            (r'(.+?)因此(.+?)。', '{}因此{}'),
            (r'(.+?)所以(.+?)。', '{}所以{}'),
        ]
        
        causality_chain = []
        
        for pattern, template in causality_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                causality_chain.append({
                    "cause": match[0].strip(),
                    "effect": match[1].strip(),
                    "template": template
                })
        
        return causality_chain
    
    def detect_patterns(self, texts: list) -> dict:
        """
        检测文本模式
        
        Args:
            texts: 文本列表
        
        Returns:
            dict: 检测到的模式
        """
        if not texts:
            return {"patterns": [], "common_keywords": []}
        
        # 提取所有关键词
        all_keywords = []
        for text in texts:
            words = text.split()
            for word in words:
                if len(word) >= 2:
                    all_keywords.append(word.lower())
        
        # 统计词频
        keyword_freq = {}
        for keyword in all_keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        # 找到高频词（出现>=2次）
        common_keywords = [k for k, v in keyword_freq.items() if v >= 2]
        
        return {
            "patterns": [],
            "common_keywords": common_keywords[:10]
        }
    
    def extract_insights(self, text: str) -> dict:
        """
        提取文本中的洞察（LLM增强）
        
        Args:
            text: 待分析的文本
        
        Returns:
            dict: 洞察结果
        """
        if self.llm:
            try:
                return self.llm.extract_insights(text)
            except Exception:
                pass
        
        # 回退到基础分析
        analysis = self._basic_analyze(text)
        return {
            "core_insight": analysis["key_sentences"][0] if analysis["key_sentences"] else "",
            "implications": [],
            "actionable": [],
            "connections": []
        }
    
    def suggest_links(self, page_content: str, other_pages: List[dict]) -> List[dict]:
        """
        建议页面间的链接（LLM增强）
        
        Args:
            page_content: 当前页面内容
            other_pages: 其他页面列表
        
        Returns:
            list: 链接建议
        """
        if self.llm:
            try:
                return self.llm.suggest_links(page_content, other_pages)
            except Exception:
                pass
        
        return []
    
    def _get_node_by_id(self, node_id: str) -> Optional[dict]:
        """根据ID获取节点"""
        for node in self.data["nodes"]:
            if node["id"] == node_id:
                return node
        return None


# 便捷函数
def create_reasoning_engine(data_dir: str = None, use_llm: bool = True) -> ReasoningEngine:
    """创建推理引擎实例"""
    return ReasoningEngine(data_dir, use_llm)


if __name__ == "__main__":
    # 测试
    engine = ReasoningEngine()
    
    # 分析测试
    text = "Python是一种编程语言，它简单易学。Python广泛应用于数据分析、人工智能等领域。"
    analysis = engine.analyze(text)
    print(f"分析结果: {analysis}")
    
    # 总结测试
    summary = engine.summarize(text)
    print(f"总结结果: {summary}")
