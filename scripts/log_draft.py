# -*- coding: utf-8 -*-
"""
log_draft.py — 从 git log 生成日志草稿

用法：
    python .workbuddy/scripts/log_draft.py

输出：
    结构化 Markdown 表格行，AI 审核后追加到日志.md

原理：
    读取自上次写日志后的 git commit，解析 commit msg 生成结构化条目。
    commit msg 格式：`类型: 摘要`（如 feat: 新增待审清单）
"""

import subprocess
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ---------- 获取自今天开始的 commit ----------
today = datetime.now().strftime('%Y-%m-%d')

result = subprocess.run(
    ['git', 'log', f'--after={today} 00:00', '--oneline', '--format=%H|%s|%ai'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', cwd='.'
)

if not result.stdout.strip():
    print('今天没有新的 commit')
    sys.exit(0)

# ---------- 类型映射 ----------
TYPE_MAP = {
    'feat': 'feat',
    'fix': 'fix',
    'lint': 'lint',
    'review': 'review',
    'update': 'update',
    'ingest': 'ingest',
    'refactor': 'refactor',
    'cleanup': 'cleanup',
    'docs': 'docs',
    'style': 'style',
}

TYPE_EMOJI = {
    'feat': '✨',
    'fix': '🔧',
    'lint': '🔍',
    'review': '👁',
    'update': '📝',
    'ingest': '📥',
    'refactor': '♻️',
    'cleanup': '🧹',
    'docs': '📖',
}

lines = []
for line in result.stdout.strip().split('\n'):
    parts = line.split('|')
    if len(parts) != 3:
        continue
    sha, msg, time_str = parts

    # 解析时间
    try:
        dt = datetime.strptime(time_str[:16], '%Y-%m-%d %H:%M')
        time_str = dt.strftime('%H:%M')
    except:
        time_str = '--:--'

    # 解析类型
    type_raw = msg.split(':')[0] if ':' in msg else 'other'
    type_clean = TYPE_MAP.get(type_raw, 'other')
    emoji = TYPE_EMOJI.get(type_clean, '')

    # 解析摘要（去掉类型前缀）
    summary = msg.split(':', 1)[1].strip() if ':' in msg else msg

    # 尝试提取关联链接（[[])）
    ref = ''
    if '[[' in summary and ']]' in summary:
        start = summary.index('[[')
        ref = summary[start:]
        summary = summary[:start].strip().rstrip(',')

    lines.append({
        'time': time_str,
        'type': type_clean,
        'summary': summary,
        'emoji': emoji,
        'ref': ref,
        'sha': sha[:7],
    })

# ---------- 输出 ----------
print(f'## {today}')
print()
print('| 时间 | AI | 类型 | 操作 | 关联 |')
print('|:----:|:--:|:----:|------|:----:|')

for l in lines:
    type_str = f'{l["emoji"]} {l["type"]}' if l['emoji'] else l['type']
    print(f'| {l["time"]} | WB | {type_str} | {l["summary"]} | {l["ref"]} |')

print()
print(f'--- 共 {len(lines)} 条 commit ---')
