# -*- coding: utf-8 -*-
"""
灵台灵识 - 测试脚本
===================
验证所有模块是否正常工作。
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_engine import MemoryEngine
from auto_edge import AutoEdge
from reasoning_engine import ReasoningEngine
from token_monitor import TokenMonitor


def test_memory_engine():
    """测试记忆引擎"""
    print("=" * 50)
    print("测试记忆引擎")
    print("=" * 50)
    
    engine = MemoryEngine()
    
    # 查询测试
    query_result = engine.query("AI")
    results = query_result.get("results", [])
    print(f"查询'AI': {len(results)} 条结果 (match_type: {query_result.get('match_type', 'N/A')})")
    for p in results[:3]:
        print(f"  - {p['title']}: {p['summary'][:50]}...")
    
    # 图扩散搜索
    graph_results = engine.search_graph("AI", hops=1)
    print(f"图扩散搜索'AI': {len(graph_results)} 条结果")
    
    # 统计
    stats = engine.get_stats()
    print(f"统计: {stats['total_pages']} 页, {stats['total_links']} 链接")
    
    print("记忆引擎测试完成！\n")


def test_auto_edge():
    """测试自动建边"""
    print("=" * 50)
    print("测试自动建边")
    print("=" * 50)
    
    auto_edge = AutoEdge()
    
    # 链接分析
    analysis = auto_edge.analyze_links()
    print(f"链接分析:")
    print(f"  总页面: {analysis['total_pages']}")
    print(f"  总链接: {analysis['total_links']}")
    print(f"  孤立页面: {analysis['isolated_count']}")
    
    # 枢纽页面
    print(f"枢纽页面 (Top 5):")
    for hub in analysis['hub_pages'][:5]:
        print(f"  - {hub['title']}: {hub['backlinks']} 个入链")
    
    print("自动建边测试完成！\n")


def test_reasoning_engine():
    """测试推理引擎"""
    print("=" * 50)
    print("测试推理引擎")
    print("=" * 50)
    
    engine = ReasoningEngine()
    
    # 分析测试
    text = "Python是一种编程语言，它简单易学。Python广泛应用于数据分析、人工智能等领域。"
    analysis = engine.analyze(text)
    print(f"分析结果: {analysis}")
    
    # 总结测试
    summary = engine.summarize(text)
    print(f"总结结果: {summary}")
    
    # 因果链提取
    causality_text = "因为用户需求增加，所以系统需要扩容。由于服务器负载过高，导致响应变慢。"
    causality = engine.extract_causality(causality_text)
    print(f"因果链: {causality}")
    
    print("推理引擎测试完成！\n")


def test_token_monitor():
    """测试Token监测"""
    print("=" * 50)
    print("测试Token监测")
    print("=" * 50)
    
    monitor = TokenMonitor()
    
    # 记录使用
    monitor.record_usage("query", "hunyuan-turbos", 100, 50, 80)
    monitor.record_usage("search", "hunyuan-turbos", 50, 30, 40)
    
    # 获取节省统计
    savings = monitor.get_savings()
    print(f"节省统计: {savings}")
    
    # 获取费用汇总
    cost_summary = monitor.get_cost_summary(days=1)
    print(f"费用汇总: {cost_summary}")
    
    # 获取操作统计
    action_stats = monitor.get_action_stats()
    print(f"操作统计: {action_stats}")
    
    print("Token监测测试完成！\n")


def main():
    """主测试函数"""
    print("灵台灵识模块测试")
    print("=" * 50)
    
    try:
        test_memory_engine()
        test_auto_edge()
        test_reasoning_engine()
        test_token_monitor()
        
        print("=" * 50)
        print("所有测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
