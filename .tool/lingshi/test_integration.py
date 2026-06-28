# -*- coding: utf-8 -*-
"""
灵台灵识 - 集成测试脚本
=======================
测试灵识模块与灵台系统的集成。
"""

import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lingtai_integration import LingtaiIntegration


def test_integration():
    """测试集成功能"""
    print("=" * 60)
    print("灵台灵识集成测试")
    print("=" * 60)
    
    # 创建集成实例
    vault_path = r"os.environ.get("LINGTAI_VAULT", "")"
    integration = LingtaiIntegration(vault_path)
    
    # 测试1: 查询知识
    print("\n1. 测试查询知识:")
    result1 = integration.query_from_dantang("AI")
    print(f"   找到 {result1['total_found']} 条相关知识")
    for item in result1['direct_matches'][:3]:
        print(f"   - {item['title']}: {item['summary'][:50]}...")
    
    # 测试2: 分析页面链接
    print("\n2. 测试分析页面链接:")
    result2 = integration.analyze_page_links("丹房/00-思考与认知/含人量")
    print(f"   相关页面: {result2['related_count']}")
    print(f"   潜在关联: {result2['potential_count']}")
    print(f"   链接建议: {len(result2['suggestions'])}")
    
    # 测试3: 获取统计
    print("\n3. 测试获取统计:")
    stats = integration.get_lingshi_stats()
    print(f"   总页面: {stats['memory']['total_pages']}")
    print(f"   总链接: {stats['memory']['total_links']}")
    print(f"   Token消耗: {stats['tokens']['today']['consumed']} tokens")
    
    print("\n" + "=" * 60)
    print("集成测试完成！")
    print("=" * 60)


def test_ll_finish_with_brain():
    """测试增强版的 ll_finish.py"""
    print("\n" + "=" * 60)
    print("测试 ll_finish_with_brain.py (灵识版)")
    print("=" * 60)
    
    # 检查文件是否存在
    script_path = Path(__file__).parent.parent / "scripts" / "ll_finish_with_brain.py"
    if script_path.exists():
        print(f"✅ 增强版脚本已创建: {script_path}")
        print("\n使用方法:")
        print(f"  python {script_path} 原料/xxx.md \"丹房/域/页名\" \"摘要\" 补角")
    else:
        print(f"❌ 增强版脚本不存在: {script_path}")


def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 60)
    print("灵台灵识使用说明")
    print("=" * 60)
    
    print("""
1. 命令行使用:

   # 查询知识
   python 灵台/.tool/lingshi/lingtai_integration.py query "关键词"

   # 分析页面链接
   python 灵台/.tool/lingshi/lingtai_integration.py analyze "丹房/00-思考与认知/含人量"

   # 全库链接分析
   python 灵台/.tool/lingshi/lingtai_integration.py links

   # 查看统计
   python 灵台/.tool/lingshi/lingtai_integration.py stats

2. Python代码使用:

   from .tool.lingshi import LingtaiIntegration

   integration = LingtaiIntegration()

   # 查询
   results = integration.query_from_dantang("关键词")

   # 分析页面链接
   analysis = integration.analyze_page_links("丹房/00-思考与认知/含人量")

   # 统计
   stats = integration.get_lingshi_stats()

3. 在提炼流程中使用:

   # 使用增强版的 ll_finish.py
   python 灵台/.tool/scripts/ll_finish_with_brain.py 原料/xxx.md "丹房/域/页名" "摘要" 补角
""")


if __name__ == "__main__":
    try:
        test_integration()
        test_ll_finish_with_brain()
        show_usage()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
