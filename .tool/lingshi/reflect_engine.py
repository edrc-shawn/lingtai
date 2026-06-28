# -*- coding: utf-8 -*-
"""
灵台灵识 - 主动反思引擎（Reflect Engine）
===========================================
基于 Hindsight 设计，定期主动回顾知识库，发现知识缺口。

检查项：
1. 知识缺口 - 原料中有但丹房中未提炼的内容
2. 断裂关联 - 有语义关联但无双向链接的页面
3. 过时内容 - 长时间未更新/未被引用的页面
4. 模式涌现 - 多个原料共同指向一个未提炼的主题
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Finding:
    """检查发现"""
    type: str
    topic: str
    severity: float  # 0-1
    detail: str
    suggestion: str
    
    def to_dict(self) -> dict:
        return asdict(self)


class ReflectEngine:
    """主动反思引擎"""
    
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
        
        self.丹房 = Path(self.vault_path) / "丹房"
        self.原料 = Path(self.vault_path) / "原料"
        self.report_path = Path(self.vault_path) / "体检" / "reflect_report.md"
    
    def reflect(self, depth: str = "standard") -> dict:
        """
        全量反思
        
        Args:
            depth: 深度（quick/standard/deep）
        
        Returns:
            dict: 反思报告
        """
        findings = []
        
        # 执行各项检查
        findings.extend(self._check_knowledge_gaps())
        findings.extend(self._check_stale_content())
        
        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "depth": depth,
            "findings": [f.to_dict() for f in findings],
            "total_findings": len(findings),
            "high_severity": sum(1 for f in findings if f.severity >= 0.7),
            "medium_severity": sum(1 for f in findings if 0.4 <= f.severity < 0.7),
            "low_severity": sum(1 for f in findings if f.severity < 0.4),
        }
        
        return report
    
    def _check_knowledge_gaps(self) -> List[Finding]:
        """检查知识缺口：原料中有但丹房中未提炼的内容"""
        findings = []
        
        # 获取原料文件
        if not self.原料.exists():
            return findings
        
        raw_files = list(self.原料.glob("*.md"))
        
        # 获取丹房页面
        if not self.丹房.exists():
            return findings
        
        danfang_files = []
        for f in self.丹房.rglob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                if "处理状态: 已提炼" not in content and "处理状态: 待提炼" not in content:
                    danfang_files.append(f.stem)
            except:
                pass
        
        # 检查未提炼的原料
        for raw_file in raw_files:
            try:
                content = raw_file.read_text(encoding="utf-8")
                if "处理状态: 待提炼" in content:
                    # 提取标题
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    title = title_match.group(1) if title_match else raw_file.stem
                    
                    findings.append(Finding(
                        type="knowledge_gap",
                        topic=title,
                        severity=0.6,
                        detail=f"原料中有「{title}」尚未提炼",
                        suggestion=f"将原料提炼到丹房对应域"
                    ))
            except:
                pass
        
        return findings[:10]  # 限制返回数量
    
    def _check_stale_content(self) -> List[Finding]:
        """检查过时内容：长时间未更新/未被引用的页面"""
        findings = []
        
        if not self.丹房.exists():
            return findings
        
        now = datetime.now()
        stale_days = 90  # 90天未更新
        
        for f in self.丹房.rglob("*.md"):
            try:
                # 检查文件修改时间
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                days_since_update = (now - mtime).days
                
                if days_since_update > stale_days:
                    # 提取标题
                    content = f.read_text(encoding="utf-8")
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    title = title_match.group(1) if title_match else f.stem
                    
                    findings.append(Finding(
                        type="stale_content",
                        topic=title,
                        severity=0.4,
                        detail=f"已 {days_since_update} 天未更新",
                        suggestion=f"审阅是否仍有效，或归档/删除"
                    ))
            except:
                pass
        
        return findings[:10]  # 限制返回数量
    
    def reflect_topic(self, topic: str) -> dict:
        """
        针对特定主题的定向反思
        
        Args:
            topic: 主题关键词
        
        Returns:
            dict: 反思结果
        """
        findings = []
        
        # 搜索相关原料
        if self.原料.exists():
            for f in self.原料.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8")
                    if topic.lower() in content.lower():
                        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                        title = title_match.group(1) if title_match else f.stem
                        findings.append(Finding(
                            type="topic_related",
                            topic=title,
                            severity=0.5,
                            detail=f"原料中有关于「{topic}」的内容",
                            suggestion=f"考虑提炼到丹房"
                        ))
                except:
                    pass
        
        return {
            "topic": topic,
            "findings": [f.to_dict() for f in findings[:10]],
            "total": len(findings),
        }


# 便捷函数
def create_reflect_engine(vault_path: str = None) -> ReflectEngine:
    """创建反思引擎实例"""
    return ReflectEngine(vault_path)


if __name__ == "__main__":
    # 测试
    engine = ReflectEngine()
    
    print("反思引擎测试")
    print("=" * 50)
    
    # 全量反思
    print("\n全量反思:")
    report = engine.reflect()
    print(f"  发现数: {report['total_findings']}")
    print(f"  高严重度: {report['high_severity']}")
    print(f"  中严重度: {report['medium_severity']}")
    print(f"  低严重度: {report['low_severity']}")
    
    # 显示发现
    for finding in report['findings'][:5]:
        print(f"\n  [{finding['type']}] {finding['topic']}")
        print(f"    严重度: {finding['severity']}")
        print(f"    详情: {finding['detail']}")
        print(f"    建议: {finding['suggestion']}")
    
    # 定向反思
    print("\n定向反思 'Python':")
    result = engine.reflect_topic("Python")
    print(f"  发现数: {result['total']}")
    
    print("\n✅ 测试完成")
