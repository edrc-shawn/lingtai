#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lingtai.py — 零台 CLI 入口

用法：
    python lingtai.py init [--name <你的名字>]
    python lingtai.py check
    python lingtai.py help

init:  初始化本地灵台知识库（首次使用）
check: 检查环境依赖
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS_DIR = VAULT_ROOT / "scripts"

# ── 丹房域模板 ──────────────────────────────────
DANFANG_DOMAINS = [
    ("00-思考与认知", "追问/O与π/含人量/独立思考/认知升级"),
    ("01-内容创作", "公众号/短视频/小红书/选题/爆款/文案"),
    ("02-成长与日常", "个人成长/日常反思/自律"),
    ("03-社会观察", "社会批判/规训/叙事消费/社会达尔文"),
    ("04-身体与健康", "减脂/跑步/篮球/营养/运动"),
    ("05-哲学与思想", "易经/道家/权力/文明/拆字"),
    ("06-商业与投资", "创业/投资/变现/副业/商业模式"),
    ("07-工具与AI", "AI工具/Obsidian/编程/智能体"),
    ("08-教育", "教育/学习/费曼/育儿/学校"),
]


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
    """检查环境依赖"""
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
        print("  ⚠ Git 未找到（init 仍可用，但建议安装）")

    if (VAULT_ROOT / "索引.md").exists():
        print("  ✅ 灵台模板文件完整")
    else:
        print("  ❌ 模板文件缺失，请重新 clone")
        ok = False

    return ok


def init_vault(name: str | None = None):
    """初始化灵台知识库"""
    print(f"\n🏗️  初始化灵台知识库...")

    created = 0
    skipped = 0

    # 1. 创建丹房域目录
    print("\n📁 创建丹房目录...")
    danfang = VAULT_ROOT / "丹房"
    for domain, _desc in DANFANG_DOMAINS:
        d = danfang / domain
        if not d.exists():
            d.mkdir(parents=True)
            print(f"  + {domain}")
            created += 1
        else:
            skipped += 1

    # 2. 创建原料目录
    yuanliao = VAULT_ROOT / "原料"
    if not yuanliao.exists():
        yuanliao.mkdir(parents=True)
        print("  + 原料/")
        created += 1

    # 3. 画像
    portrait_src = VAULT_ROOT / "入门" / "画像.template.md"
    portrait_dst = VAULT_ROOT / "入门" / "灵台用户画像.md"
    if portrait_src.exists() and not portrait_dst.exists():
        shutil.copy(portrait_src, portrait_dst)
        print(f"\n🖼️  画像模板已复制: 入门/灵台用户画像.md")
        print("   （可选）编辑此文件填入你的偏好，AI 会融入角色")
        created += 1

    # 4. .gitignore
    gitignore = VAULT_ROOT / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# 灵台用户私有文件\n入门/灵台用户画像.md\n原料/*\n丹房/*\n日志.md\n.obsidian/workspace.json\n",
            encoding="utf-8",
        )
        print("  + .gitignore（原料/丹房/日志/画像已排除）")
        created += 1

    print(f"\n📊 新建 {created} 项，已存在 {skipped} 项")

    # 5. 输出下一步
    name_str = f"，{name}" if name else ""
    print(f"""
{'='*50}
  灵台已就绪{name_str}！

  下一步:
  1. 用 Obsidian 打开本文件夹作为 vault
  2. 放入原料:  将 Markdown/笔记 拖入 原料/
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

    if cmd == "help" or cmd == "-h" or cmd == "--help":
        print(__doc__)
    elif cmd == "check":
        check_env()
    elif cmd == "init":
        name = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == "--name" and i + 1 < len(sys.argv[2:]):
                name = sys.argv[2:][i + 1]
        init_vault(name)
    else:
        print(f"未知命令: {cmd}\n")
        print(__doc__)


if __name__ == "__main__":
    main()
