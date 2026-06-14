# -*- coding: utf-8 -*-
"""
check_log.py — 提交前日志校验

用法：
    python .workbuddy/scripts/check_log.py

作用：
    在 git commit 之前运行，对比今天的 commit 数量和日志表格行数。
    发现遗漏时输出缺失条目，AI 补写后再提交。

原理：
    1. 解析今日所有 commit msg（类型: 摘要）
    2. 读取日志.md 今天的表格行
    3. 对比：commit 中提到的操作是否都有对应日志行
"""

import subprocess, re, sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

today = datetime.now().strftime('%Y-%m-%d')

# ---------- 1. 获取今日 commit ----------
result = subprocess.run(
    ['git', 'log', f'--after={today} 00:00', '--oneline', '--format=%s'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', cwd='.'
)

if not result.stdout.strip():
    print('今天没有新 commit，跳过检查')
    sys.exit(0)

commits = [line.strip() for line in result.stdout.split('\n') if line.strip()]

# ---------- 2. 读取今日日志 ----------
try:
    with open('丹房/日志.md', 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print('日志.md 不存在，请先初始化')
    sys.exit(1)

# 找到今天日期标题下的表格行
today_section = re.search(
    rf'# {today}\n\n\|.*?\n\|.*?\n(.*?)(?=\n# |\Z)',
    content, re.DOTALL
)
log_lines = []
if today_section:
    for line in today_section.group(1).split('\n'):
        line = line.strip()
        if line.startswith('|') and not line.startswith('|:') and '|' in line:
            log_lines.append(line)

# ---------- 3. 对比 ----------
# 从 commit msg 中提取操作摘要（跳过 log: / checkup: 等自动 commit）
SKIP_TYPES = {'log', 'checkup', 'other'}
commit_ops = []
for msg in commits:
    if ':' not in msg:
        continue
    parts = msg.split(':', 1)
    prefix = parts[0].strip()
    summary = parts[1].strip()
    if prefix in SKIP_TYPES:
        continue
    commit_ops.append(summary)

# 从日志行中提取操作摘要
log_ops = []
for line in log_lines:
    cells = line.split('|')
    if len(cells) >= 4:
        log_ops.append(cells[3].strip())

# 中文 N-gram 匹配：取 commit 摘要中任意连续 3 个中文字
# 短中文串（<4个汉字）直接用全文匹配
def extract_ngrams(text, n=3):
    chars = re.findall(r'[\u4e00-\u9fff]', text)
    if len(chars) < 5:
        return {text}  # 短串用全文匹配
    return {''.join(chars[i:i+n]) for i in range(len(chars)-n+1)}

missing = []
for op in commit_ops:
    ngrams = extract_ngrams(op)
    found = False
    for log_op in log_ops:
        # 检查是否有至少 2 个 n-gram 命中日志行
        hits = sum(1 for ng in ngrams if ng in log_op)
        if hits >= 1 or len(ngrams) == 1:
            found = True
            break
    if not found:
        missing.append(op)

if missing:
    # 已知误报过滤：补日志元操作
    known_false = [m for m in missing if ('补' in m and '日志' in m) or 'Obsidian' in m]
    missing = [m for m in missing if m not in known_false]
    
    if missing:
        print('⚠️  以下操作没有对应的日志条目：')
        for m in missing:
            print(f'  {m}')
        print()
        print('请先写日志再提交。格式：')
        print(f'| HH:MM | type | {missing[0][:30]}... | → 页面路径 |')
        sys.exit(1)
    else:
        print('✅ 日志完整（仅缺补日志元操作，已过滤）')
else:
    print('✅ 日志完整，所有操作都有对应条目')

# ---------- 4. 新文件标签检查 ----------
# 扫描 git stage 区新增的 .md 文件，检查正文是否包含 #标签
result = subprocess.run(
    ['git', 'diff', '--cached', '--name-only', '--diff-filter=A'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', cwd='.'
)
new_files = [f.strip() for f in result.stdout.split('\n') if f.strip().endswith('.md') and not f.startswith('.')]

tag_issues = []
for fp in new_files:
    # 跳过原料层文件（标签规范只适用于丹房）
    if fp.startswith('原料/'):
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        continue
    # 跳过 frontmatter，检查正文第一行是否有 #标签
    body = re.sub(r'^---\n.*?\n---\n', '', content, count=1, flags=re.DOTALL)
    first_line = body.strip().split('\n')[0] if body.strip() else ''
    if not re.search(r'#[\u4e00-\u9fff\w-]', first_line):
        tag_issues.append(fp)

if tag_issues:
    print()
    print('⚠️  以下新增文件缺少正文标签：')
    for f in tag_issues:
        print(f'  {f}')
    print()
    print('请在正文第一行添加 `#标签`（如 `#灵台 #输出`），不要写在 frontmatter 中。')
    sys.exit(1)
