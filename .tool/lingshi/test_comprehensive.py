# -*- coding: utf-8 -*-
"""
灵台灵识 - 综合测试脚本
=======================
模拟灵台实际使用场景，测试各模块的协同工作。
"""

import sys
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_engine import MemoryEngine
from auto_edge import AutoEdge
from reasoning_engine import ReasoningEngine
from token_monitor import TokenMonitor


def test_query_workflow():
    """测试问知流程（模拟灵台的查询流程）"""
    print("=" * 60)
    print("测试问知流程（查询→回答）")
    print("=" * 60)
    
    memory = MemoryEngine()
    reasoning = ReasoningEngine()
    token_monitor = TokenMonitor()
    
    # 模拟用户问题
    questions = [
        "Python是什么？",
        "机器学习和深度学习有什么关系？",
        "Python在人工智能中的应用"
    ]
    
    for question in questions:
        print(f"\n问题: {question}")
        
        # 查询知识
        results = memory.query(question)
        print(f"   → 直接匹配: {len(results)} 条")
        
        # 图扩散搜索
        graph_results = memory.search_graph(question, hops=1)
        print(f"   → 关联知识: {len(graph_results)} 条")
        
        # 推理分析
        if results:
            combined_text = " ".join([p.get("summary", "") for p in results[:3]])
            analysis = reasoning.analyze(combined_text)
            print(f"   → 关键词: {analysis['keywords'][:5]}")
        
        # 记录Token使用
        token_monitor.record_usage("query", "hunyuan-turbos", 80, 120, 60)


def test_edge_analysis():
    """测试链接分析"""
    print("\n" + "=" * 60)
    print("测试链接分析")
    print("=" * 60)
    
    auto_edge = AutoEdge()
    
    # 链接分析
    analysis = auto_edge.analyze_links()
    print(f"\n链接分析:")
    print(f"  总页面: {analysis['total_pages']}")
    print(f"  总链接: {analysis['total_links']}")
    print(f"  孤立页面: {analysis['isolated_count']}")
    
    # 枢纽页面
    print(f"\n枢纽页面 (Top 5):")
    for hub in analysis['hub_pages'][:5]:
        print(f"  - {hub['title']}: {hub['backlinks']} 个入链")


def test_reasoning_capabilities():
    """测试推理引擎的能力"""
    print("\n" + "=" * 60)
    print("测试推理引擎能力")
    print("=" * 60)
    
    engine = ReasoningEngine()
    
    # 测试因果链提取
    causality_text = """
    因为用户需求不断增加，所以系统需要进行扩容。
    由于服务器负载过高，导致响应时间变慢。
    为了提高用户体验，因此引入了缓存机制。
    """
    
    print("\n1. 因果链提取：")
    causality = engine.extract_causality(causality_text)
    for item in causality:
        print(f"   原因: {item['cause']}")
        print(f"   结果: {item['effect']}")
        print()
    
    # 测试文章总结
    long_text = """
    人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能才能完成的任务的系统。
    机器学习是AI的核心技术之一，它使计算机能够从数据中学习。
    深度学习是机器学习的一个子集，使用多层神经网络。
    自然语言处理（NLP）是AI的另一个重要领域，专注于使计算机理解和生成人类语言。
    计算机视觉则专注于使计算机能够从图像和视频中提取信息。
    """
    
    print("2. 文章总结：")
    summary = engine.summarize(long_text, max_length=100)
    print(f"   {summary}")


def test_token_monitoring():
    """测试Token监测功能"""
    print("\n" + "=" * 60)
    print("测试Token监测功能")
    print("=" * 60)
    
    monitor = TokenMonitor()
    
    # 获取统计
    print("\n1. 当前统计:")
    savings = monitor.get_savings()
    print(f"   今日消耗: {savings['today']['consumed']} tokens")
    print(f"   今日节省: {savings['today']['saved']} tokens")
    print(f"   节省率: {savings['today']['saved']/max(savings['today']['consumed'],1)*100:.1f}%")
    
    # 生成报告
    print("\n2. 每日报告:")
    report = monitor.generate_daily_report()
    print(report)


def main():
    """主测试函数"""
    print("灵台灵识 - 综合测试")
    print("=" * 60)
    
    try:
        # 运行测试
        test_query_workflow()
        test_edge_analysis()
        test_reasoning_capabilities()
        test_token_monitoring()
        
        print("\n" + "=" * 60)
        print("所有综合测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
