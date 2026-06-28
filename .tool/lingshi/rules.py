# -*- coding: utf-8 -*-
"""
灵台灵识 - 台律规则模块
========================
纯硬编码规则查询。台律.md 已退役，规则由内联 prompt + 本模块兜底。
"""


class LingtaiRules:
    """灵台台律规则查询（无文件依赖）"""
    
    def __init__(self, vault_path: str = None):
        pass

    def get_rules(self, chapter: str = "all") -> dict:
        """
        获取台律规则（全硬编码）
        
        Args:
            chapter: 章节（all/身份/字段/格式/约束/索引/提炼/体检）
        """
        rules = {
            "身份": "灵台整理引擎。不编造（一切可追溯到原料原文），文件名禁止引号，双链精度三阶（[[整页]] / [[页#节|别名]] / [[原料/xxx^块]]），新旧矛盾保留双方不取舍，原料只读（仅加 FM + 回链）。",
            "字段": "丹房页必填：标题/日期/类型(提炼|对话)。品级：下品(单源)/中品(交叉)/上品(≥3内联引用)。状态：活跃/占位/已停用。自动维护：原料数量/职责。原料页必填：处理状态(待提炼|已提炼|已跳过)/处理日期/提炼摘要。回链：→ [[丹房/域/页]] 放正文末尾。",
            "格式": "主题页结构：frontmatter → ## 摘要 → ## 要点 → 推荐阅读。链接三阶：①[[整页]] ②[[页#节|别名]] ③[[原料/xxx^块]]。推荐阅读 3-15 条，去重、不同域优先、不链自己。分流表：补强(融入脚注)/补角(新建节)/佐证(行内脚注)/对立(⚡矛盾)/挑战(⚡挑战)/框架变更(需确认)。上品页补角/对立/挑战仅挂递条不改写正文。",
            "约束": "1.不编造 2.不删原文 3.不覆盖(同名合并冲突留双方) 4.不评价 5.不遗漏来源 6.不自动删除 7.不自动修复(拆页除外) 8.台律修改需确认。",
            "索引": "索引.md 已退役(26-06-27)。人类导航→入门/路由表.md。LLM 找页→丹房/.meta/export/by_domain/*.md(build_index.py自动生成)。快查→丹房/.meta/export/quick_ref.json。日志格式：[YY-MM-DD HH:MM] 类型 | 操作描述 | → 路径。",
            "提炼": "选料→find_shortest_pending.py。读料→lingshi_query 或 .meta/export/by_domain/。分流→补强/补角/佐证/对立/挑战。收尾→ll_finish.py。FM字段和链接精度见内联规则。",
            "体检": "每日检→lint_check.py。每周查→语义探针+知识缺口。每月问→时效检查+台律演化建议。",
        }
        
        if chapter == "all":
            return rules
        elif chapter in rules:
            return {chapter: rules[chapter]}
        else:
            return {"error": f"未知章节: {chapter}"}

    def get_filename_rules(self) -> dict:
        return {
            "rule": "文件名禁止使用引号",
            "forbidden": ["弯引号 U+201C", "弯引号 U+201D", "直引号 U+0022"],
            "alternative": "改用直角引号「」或直接去掉",
            "check": "建新文件前自动检查，发现引号立即退回修正",
        }

    def get_link_rules(self) -> dict:
        return {
            "整页引用": "[[整页]] — 引用整页主题",
            "锚点引用": "[[所在页#具体小节|显示文字]] — 引用具体论点",
            "块引用": "[[原料/xxx^块标记]] — 指向原料某一段落",
            "禁止": "正文中禁止裸写让句子读不通的长 wikilink（必须用 | 改显示文字）",
        }

    def get_field_rules(self) -> dict:
        return {
            "丹房页面": {
                "必填": ["标题", "日期", "类型"],
                "自动维护": ["原料数量", "状态", "职责"],
                "品级": ["下品", "中品", "上品"],
            },
            "原料页面": {
                "必填": ["处理状态", "处理日期", "提炼摘要"],
                "回链": "→ [[丹房/域-描述语/目标页]] 放在正文末尾",
            },
        }


# 便捷函数
def create_rules(vault_path: str = None) -> LingtaiRules:
    return LingtaiRules(vault_path)
