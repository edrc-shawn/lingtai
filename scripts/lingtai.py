#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lingtai.py — 零台 CLI 入口

用法：
    python lingtai.py init              交互式选择职业模板初始化
    python lingtai.py check             检查环境依赖
    python lingtai.py help              帮助

init 选项（非交互式）：
    python lingtai.py init --template=creator    内容创作者模板
    python lingtai.py init --template=programmer 程序员模板
    python lingtai.py init --template=business   商业/管理模板
    python lingtai.py init --template=custom     自定义域，用 --domains 指定
        --domains="00-XX,01-YY,02-ZZ"            自定义域列表
    python lingtai.py init --name "你的名字"      可选，指定名字
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()

# ── 职业模板 ──────────────────────────────────────
TEMPLATES = {
    "creator": {
        "name": "内容创作者",
        "domains": [
            ("00-思考与认知", "追问/O与π/独立思考/认知升级"),
            ("01-内容创作", "公众号/短视频/小红书/选题/爆款/文案"),
            ("02-成长与日常", "个人成长/日常反思/自律"),
            ("03-社会观察", "社会批判/规训/叙事消费"),
            ("04-哲学与思想", "易经/道家/权力/文明"),
            ("05-商业与投资", "创业/变现/副业/商业模式"),
            ("06-工具与AI", "AI工具/Obsidian/编程"),
            ("07-教育", "教育/学习/费曼/育儿"),
        ],
    },
    "programmer": {
        "name": "程序员",
        "domains": [
            ("00-编程语言", "Python/JavaScript/Rust/Go/语法/特性"),
            ("01-框架与工具", "React/Vue/Django/Spring/工具链"),
            ("02-系统设计", "架构/分布式/微服务/高并发"),
            ("03-数据结构与算法", "排序/搜索/图/动态规划/复杂度"),
            ("04-数据库", "MySQL/Redis/MongoDB/Postgres/ES"),
            ("05-DevOps", "Docker/K8s/CI-CD/监控/部署"),
            ("06-安全", "认证/加密/漏洞/审计"),
            ("07-产品思维", "需求/用户体验/项目管理"),
        ],
    },
    "business": {
        "name": "商业/管理",
        "domains": [
            ("00-行业洞察", "趋势/政策/竞争格局/报告"),
            ("01-商业模式", "盈利模式/定价/GMV/单位经济"),
            ("02-市场与营销", "获客/品牌/渠道/增长"),
            ("03-财务与风控", "成本/现金流/融资/审计"),
            ("04-组织与人才", "管理/招聘/激励/文化建设"),
            ("05-战略与决策", "定位/杠杆/判断/复盘"),
            ("06-政策与法规", "合规/税务/合同/知识产权"),
            ("07-认知与判断", "思维模型/决策偏误/学习"),
        ],
    },
}


def run(cmd: list[str], silent: bool = False) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=VAULT_ROOT)
        if not silent and result.stderr:
            print(f"  ⚠ {result.stderr.strip()}")
        return result.stdout.strip()
    except Exception as e:
        print(f"  ❌ 命令失败: {' '.join(cmd)} — {e}")
        return ""


def check_env() -> bool:
    print("🔍 检查环境...")
    ok = True

    py = shutil.which("python3") or shutil.which("python")
    if py:
        print(f"  ✅ Python: {run([py, '--version'], silent=True)}")
    else:
        print("  ❌ Python 未找到，请安装 Python 3.10+")
        ok = False

    git = shutil.which("git")
    if git:
        print(f"  ✅ Git: {run(['git', '--version'], silent=True)}")
    else:
        print("  ⚠ Git 未找到")

    if (VAULT_ROOT / "AGENTS.md").exists():
        print("  ✅ 零台模板文件完整")
    else:
        print("  ❌ 模板文件缺失，请重新 clone")
        ok = False

    return ok


def show_templates():
    print("\n📋 可选职业模板：")
    for key, tmpl in TEMPLATES.items():
        names = ", ".join(d[0] for d in tmpl["domains"])
        print(f"  [{key:12s}] {tmpl['name']} — {names}")


def create_danfang(domains: list[tuple[str, str]]):
    danfang = VAULT_ROOT / "丹房"
    created = skipped = 0
    print("\n📁 创建丹房目录...")
    for domain, desc in domains:
        d = danfang / domain
        if not d.exists():
            d.mkdir(parents=True)
            print(f"  +  {domain}  （{desc}）")
            created += 1
        else:
            skipped += 1
    return created, skipped


def create_common():
    created = 0
    
    # 原料目录
    yuanliao = VAULT_ROOT / "原料"
    if not yuanliao.exists():
        yuanliao.mkdir(parents=True)
        print("  +  原料/")
        created += 1

    # 画像
    portrait_src = VAULT_ROOT / "入门" / "画像.template.md"
    portrait_dst = VAULT_ROOT / "入门" / "灵台用户画像.md"
    if portrait_src.exists() and not portrait_dst.exists():
        shutil.copy(portrait_src, portrait_dst)
        print("\n🖼️  画像模板已复制: 入门/灵台用户画像.md")
        created += 1

    # .gitignore
    gitignore = VAULT_ROOT / ".gitignore"
    if not gitignore.exists():
        tpl_idx = VAULT_ROOT / "索引.md"
        has_content = tpl_idx.exists()
        gitignore.write_text(
            "# 灵台用户私有文件\n入门/灵台用户画像.md\n" + ("原料/*\n丹房/*\n" if not has_content else "") + "日志.md\n.obsidian/workspace.json\n",
            encoding="utf-8",
        )
        print("  +  .gitignore")
        created += 1

    return created


def init_vault(template_key: str | None = None, name: str | None = None):
    print(f"\n🏗️  初始化灵台知识库...\n")

    # 选择模板
    if template_key and template_key in TEMPLATES:
        tmpl = TEMPLATES[template_key]
        print(f"  模板：{tmpl['name']}")
        domains = tmpl["domains"]
    elif template_key == "custom":
        print("  自定义模板")
        domains = []
    elif template_key:
        print(f"  ❌ 未知模板 '{template_key}'，可选：{', '.join(TEMPLATES.keys())}")
        return
    else:
        show_templates()
        print()
        while True:
            choice = input("  选择模板 (creator/programmer/business/custom): ").strip().lower()
            if choice in TEMPLATES:
                tmpl = TEMPLATES[choice]
                print(f"  已选：{tmpl['name']}")
                domains = tmpl["domains"]
                break
            elif choice == "custom":
                print("  自定义：稍后由 AI 引导创建")
                domains = []
                break
            else:
                print(f"  无效选项，请重试")

    # 创建丹房域
    created_d, skipped_d = create_danfang(domains)

    # 创建公共目录
    created_c = create_common()

    total = created_d + created_c
    print(f"\n📊 新建 {total} 项，已存在 {skipped_d} 项")

    # 下一步指引
    tname = tmpl["name"] if not template_key == "custom" and tmpl else ""
    name_str = f"，{name}" if name else ""
    title = f"灵台已就绪{name_str}（{tname}）" if tname else f"灵台已就绪{name_str}"
    print(f"""
{'='*50}
  {title}

  下一步:
  1. 用 Obsidian 或 WorkBuddy 打开本文件夹
  2. 放入原料:  将笔记/文章丢入 原料/
  3. 填写画像:  编辑 入门/灵台用户画像.md（可选）
  4. 对 AI 说:  提炼
{'='*50}

  AI 会读取 AGENTS.md 自动启动灵台协议。
""")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd in ("help", "-h", "--help"):
        print(__doc__)
        return

    if cmd == "check":
        check_env()
        return

    if cmd == "init":
        name = None
        template_key = None
        for arg in sys.argv[2:]:
            if arg.startswith("--name="):
                name = arg.split("=", 1)[1]
            elif arg.startswith("--template="):
                template_key = arg.split("=", 1)[1]
        init_vault(template_key, name)
        return

    print(f"未知命令: {cmd}\n")
    print(__doc__)


if __name__ == "__main__":
    main()
