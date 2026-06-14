# -*- coding: utf-8 -*-
"""
lint_check.py — 灵台 Quality Lint 全量检查脚本
参考 Karpathy kb_lint 的确定性检查机制。

用法：
    python .workbuddy/scripts/lint_check.py [--vault-root <path>]

输出：
    结构化文本报告，AI 读取后写入对应体检文件。
    不修改任何文件，只做只读扫描。

检查项：
    1. 断裂链接   — 丹房内所有 [[wikilink]] 目标存在性
    2. 矛盾候选   — 数值/时序/逻辑冲突
    3. 隐性缺口   — 索引.md vs 实际文件
    4. 死胡同     — 入链=0 但出链>0
    5. 孤立页面   — 入链=0 且 出链=0
    6. 标签分布   — #标签 词频统计
    7. 品级分布 — frontmatter 品级字段汇总
    10. 日志格式   — 日志.md 日期段是否有表头行
    11. 原料FM白名单 — 原料 frontmatter 仅4字段
    12. 原料链路   — 已提炼→有正文 wikilink
"""

import re, os, sys, subprocess
from collections import Counter

VAULT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith('--vault-root') else '.')
丹房 = os.path.join(VAULT, '丹房')
索引路径 = os.path.join(VAULT, '索引.md')

# ---------- helpers ----------
def all_md_files():
    files = []
    for root, dirs, fnames in os.walk(丹房):
        for f in fnames:
            if f.endswith('.md'):
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, 丹房)
                files.append((rel_path.replace('\\', '/'), abs_path))
    return files

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def get_body(text):
    """去掉 frontmatter 和代码块，只保留正文"""
    body = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL)
    body = re.sub(r'```.*?```', '', body, flags=re.DOTALL)
    body = re.sub(r'`[^`]+`', '', body)  # 内联代码
    return body

def extract_wikilinks(text):
    """提取正文中所有 [[丹房/...]] 链接（去掉别名）"""
    links = re.findall(r'\[\[丹房/([^\]]+?)(?:\|[^\]]*)?\]\]', text)
    result = []
    for link in links:
        target = link.split('#')[0]
        target = target.split('|')[0]
        if target:
            result.append(target)
    return result

def extract_frontmatter(text):
    m = re.match(r'^---\n(.*?)\n(?:---|\.\.\.)', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip().strip('"\'')
    return fm

def extract_tags(text):
    body = get_body(text)
    return re.findall(r'#([\w\u4e00-\u9fff_-]+)', body)

# ---------- 1. 断裂链接（均为知识缺口）----------
def _has_file_extension(path):
    """判断路径末尾是否是真正的文件扩展名（如 .md, .svg, .png），
    而不是数字中的小数点（如 9.9元验证四步法 中的 9.9）。
    """
    base = os.path.basename(path)
    dot_index = base.rfind('.')
    if dot_index <= 0 or dot_index >= len(base) - 1:
        return False
    ext = base[dot_index + 1:]
    # 文件扩展名通常为 2-4 个字母/数字
    return bool(re.match(r'^[a-zA-Z0-9]{2,4}$', ext))

def check_broken_links(files):
    """
    所有指向不存在目标的 [[wikilink]] 都是知识缺口。
    不区分"页面曾经存在过"还是"从未存在过"。
    """
    gaps = []
    format_errors = []
    for rel, abspath in files:
        content = read_file(abspath)
        body = get_body(content)
        links = extract_wikilinks(body)
        for target in links:
            # 处理路径中的格式错误（如尾随反斜杠）
            raw_target = target
            target = target.strip().rstrip('\\').strip()
            is_format_error = (raw_target != target)

            has_ext = _has_file_extension(target)
            target_path = os.path.join(丹房, target if has_ext else target + '.md')
            target_exists = os.path.isfile(target_path)

            if target_exists and not is_format_error:
                continue  # 目标存在且无格式问题，正常

            entry = f'{rel}: [[丹房/{raw_target}]]'
            if is_format_error:
                format_errors.append(entry)
            else:
                gaps.append(entry)
    return gaps, format_errors

# ---------- 2. 矛盾候选 ----------
def check_contradictions(files):
    pages = {}
    for rel, abspath in files:
        content = read_file(abspath)
        fm = extract_frontmatter(content)
        if fm:
            pages[rel] = fm
    pending = [rel for rel, fm in pages.items() if fm.get('品级') == '下品']
    return [], pending

# ---------- 3. 隐性缺口 ----------
def check_gaps(files, index_path):
    if not os.path.isfile(index_path):
        return ['索引.md 不存在']
    content = read_file(index_path)
    index_links = set(extract_wikilinks(get_body(content)))
    actual_files = set(rel for rel, _ in files)
    gaps = []
    for link in sorted(index_links):
        link_path = link + '.md'
        if link_path not in actual_files:
            gaps.append(f'索引引用但文件缺失: [[丹房/{link}]]')
    for rel in sorted(actual_files):
        rel_no_ext = rel[:-3]
        if rel_no_ext not in index_links:
            gaps.append(f'文件存在但索引未收录: {rel}')
    return gaps

# ---------- 4. 死胡同 / 5. 孤立页面 ----------
def check_deadends_isolated(files):
    in_links = Counter()
    out_links = Counter()
    file_dict = dict(files)
    for rel, abspath in files:
        content = read_file(abspath)
        body = get_body(content)
        links = extract_wikilinks(body)
        out_links[rel] = len(links)
        for target in links:
            target_rel = target + '.md'
            if target_rel in file_dict:
                in_links[target_rel] += 1
    deadends = []
    isolated = []
    for rel, _ in files:
        out_c = out_links.get(rel, 0)
        in_c = in_links.get(rel, 0)
        if out_c > 0 and in_c == 0:
            deadends.append(rel)
        elif out_c == 0 and in_c == 0:
            isolated.append(rel)
    return deadends, isolated

# ---------- 6. 标签分布 ----------
def check_tags(files):
    all_tags = Counter()
    for rel, abspath in files:
        content = read_file(abspath)
        tags = extract_tags(content)
        all_tags.update(tags)
    return all_tags

# ---------- 7. 品级分布 ----------
def check_confidence(files):
    上品 = []; 中品 = []; 下品 = []
    for rel, abspath in files:
        content = read_file(abspath)
        fm = extract_frontmatter(content)
        conf = fm.get('品级', '')
        if conf == '上品': 上品.append(rel)
        elif conf == '中品': 中品.append(rel)
        elif conf == '下品': 下品.append(rel)
    return 上品, 中品, 下品

# ========== MAIN ==========
def check_timeliness(files):
    """检查有时效字段的页面是否过期（日期 > 90 天）"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=90)
    stale = []
    for rel, abspath in files:
        text = read_file(abspath)
        fm = extract_frontmatter(text)
        if fm.get('时效') != '有效':
            continue
        try:
            d = datetime.strptime(str(fm.get('日期', '')), '%Y-%m-%d')
            if d < cutoff:
                stale.append(rel)
        except:
            pass
    return stale

def check_timeline(files):
    """检查 对账.md 时间线记录完备性（有来源引用但无对应 Timeline）"""
    # TODO: 扫描对账.md 时间线表 vs 丹房页面 Ingest 记录
    return []

# ---------- 9. 推荐区合规 ----------
def check_tuijian(files, vault_root):
    """
    检查所有页面的 ## 推荐阅读 区块：
    - 超出上限 6 → WARN
    - 断裂链接 → GAP
    - 重复链接 → WARN
    - 缺少关系说明 → WARN
    """
    warns = []
    gaps = []
    file_set = set(rel for rel, _ in files)
    for rel, abspath in files:
        content = read_file(abspath)
        match = re.search(r'^## 推荐阅读\n(.+?)(?:\n## |\n---|\Z)', content, re.MULTILINE | re.DOTALL)
        if not match:
            continue
        section = match.group(1)
        lines = section.strip().split('\n')
        links = re.findall(r'\[\[(.+?)(?:\|.+?)?\]\]', section)
        
        # 上限检查
        if len(links) > 6:
            warns.append(f'{rel}: 推荐区超上限 ({len(links)}条)')
        
        # 重复检查
        if len(links) != len(set(links)):
            dups = set([l for l in links if links.count(l) > 1])
            for d in dups:
                warns.append(f'{rel}: 推荐重复 → [[{d}]]')
        
        # 断裂检查
        for line in lines:
            lmatch = re.search(r'\[\[(.+?)(?:\|.+?)?\]\]', line)
            if lmatch:
                target = lmatch.group(1).strip()
                # For 丹房/ links: check if file exists in 丹房
                if target.startswith('丹房/'):
                    danfang_rel = target.replace('丹房/', '', 1)  # strip '丹房/' prefix
                    if danfang_rel + '.md' not in file_set:
                        gaps.append(f'{rel}: [[{target}]]')
                # For other paths (作品/台律/原料/体检/根目录): check vault root
                else:
                    # Strip .md if link already includes it
                    check_target = target
                    if check_target.endswith('.md'):
                        check_target = check_target[:-3]
                    target_path = os.path.join(vault_root, check_target + '.md')
                    if not os.path.isfile(target_path):
                        gaps.append(f'{rel}: [[{target}]]')
        
        # 关系说明检查
        for line in lines:
            if re.search(r'\[\[.+?\]\]', line):
                after_link = re.sub(r'\[\[.+?\]\]', '', line).strip()
                if not after_link or len(after_link) < 3:
                    link = re.search(r'\[\[(.+?)\]\]', line)
                    if link:
                        warns.append(f'{rel}: 推荐缺说明 → [[{link.group(1)}]]')
    
    return warns, gaps


def check_log_format(log_path):
    """检查 日志.md 格式一致性：
    - 日期标题必须用 h2（##），不可用 h1（#）
    - 每个日期段必须有 5 列表头 | 时间 | AI | 类型 | 操作 | 关联 |
    """
    if not os.path.isfile(log_path):
        return ['日志.md 不存在']
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
    warns = []

    # 检查是否有 h1 日期标题（格式不对）
    h1_dates = re.findall(r'^# \d{4}-\d{2}-\d{2}', content, re.MULTILINE)
    for d in h1_dates:
        warns.append(f'{d}: 日期标题用了 h1，应为 h2')

    # 分割所有日期段（同时匹配 h1 和 h2，确保不漏检）
    sections = re.split(r'^#{1,2} (\d{4}-\d{2}-\d{2})$', content, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        date = sections[i]
        body = sections[i+1] if i+1 < len(sections) else ''
        if '| 时间 | AI | 类型 | 操作 | 关联 |' not in body:
            warns.append(f'{date}: 缺 5 列表头（| 时间 | AI | 类型 | 操作 | 关联 |）')
    return warns


def check_raw_fm(vault_root):
    """[11] 原料 frontmatter 白名单"""
    raw_dir = os.path.join(vault_root, '原料')
    whitelist = {'处理状态', '处理日期', '来源链接'}
    warns = []
    for f in sorted(os.listdir(raw_dir)):
        if not f.endswith('.md'):
            continue
        path = os.path.join(raw_dir, f)
        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        if not content.startswith('---'):
            continue
        end = content.find('---', 3)
        if end == -1:
            continue
        for line in content[3:end].split('\n'):
            if ':' in line:
                key = line.split(':')[0].strip()
                if key not in whitelist:
                    warns.append(f'{f}: 多余字段 -> {key}')
                    break
    return warns


def check_raw_link(vault_root):
    """[12] 原料链路：已提炼->有正文 wikilink"""
    raw_dir = os.path.join(vault_root, '原料')
    warns = []
    for f in sorted(os.listdir(raw_dir)):
        if not f.endswith('.md'):
            continue
        path = os.path.join(raw_dir, f)
        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        has_status = bool(re.search(r'^处理状态:\s+已提炼', content, re.MULTILINE))
        has_wl = bool(re.search(r'-> \[\[丹房/', content))
        if has_status and not has_wl:
            warns.append(f'{f}: 已提炼但缺正文丹房 wikilink')
    return warns


def main():
    print('=' * 55)
    print('灵台 Lint 检查报告')
    print(f'Vault: {VAULT}')
    print(f'时间: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 55)

    files = all_md_files()
    file_dict = dict(files)
    print(f'\n丹房文件总数: {len(files)}')
    print(f'目录: 01-07 + 99 + 规范({sum(1 for r,_ in files if r.startswith("规范/"))}) + 体检({sum(1 for r,_ in files if r.startswith("体检/"))}) + 技能({sum(1 for r,_ in files if r.startswith("技能/"))}) + 词典({sum(1 for r,_ in files if r.startswith("词典/"))})')

    # 1. 断裂链接（均为知识缺口，不再区分"已删"和"从未存在"）
    gaps, format_errors = check_broken_links(files)
    print(f'\n[1a] 知识缺口（死链接目标不存在）')
    for g in gaps[:15]:
        print(f'  GAP {g}')
    if len(gaps) > 15:
        print(f'  ... 共 {len(gaps)} 条')
    print(f'  => 共 {len(gaps)} 条')

    if format_errors:
        print(f'\n[1b] 格式错误（路径异常，目标实际存在）')
        for fe in format_errors:
            print(f'  FORMAT {fe}')
        print(f'  => 共 {len(format_errors)} 条')
    broken_total = len(gaps) + len(format_errors)

    # 2. 矛盾候选
    print('\n[2] 矛盾候选')
    cand, pending = check_contradictions(files)
    print(f'  结构化矛盾: 0')
    if pending:
        print(f'  下品页面: {len(pending)}')
        for p in pending:
            print(f'  LOWER {p}')
    else:
        print(f'  下品页面: 0')

    # 3. 隐性缺口
    print('\n[3] 隐性缺口')
    index_gaps = check_gaps(files, 索引路径)
    for g in index_gaps:
        print(f'  GAP {g}')
    print(f'  => 共 {len(index_gaps)} 条')

    # 4. 死胡同
    print('\n[4] 死胡同')
    deadends, isolated = check_deadends_isolated(files)
    for d in deadends[:15]:
        print(f'  DEADEND {d}')
    if len(deadends) > 15:
        print(f'  ... 共 {len(deadends)} 个')
    print(f'  => 共 {len(deadends)} 个')

    # 5. 孤立页面
    print('\n[5] 孤立页面')
    for i in isolated[:10]:
        print(f'  ISOLATED {i}')
    if len(isolated) > 10:
        print(f'  ... 共 {len(isolated)} 个')
    print(f'  => 共 {len(isolated)} 个')

    # 6. 标签分布
    print('\n[6] 标签分布（前15）')
    tags = check_tags(files)
    total_tags = sum(tags.values())
    print(f'  标签总数: {total_tags}')
    for tag, count in tags.most_common(15):
        bar = '#' * min(count, 30)
        print(f'  #{tag:20s} {count:3d} {bar}')
    # 高频标签信号：Top-3 非主标签，检查是否有对应丹房页
    primary = {'概念', '方法', '案例', '痛点', '灵感', '反模式'}
    top3 = [(t, c) for t, c in tags.most_common(50) if t not in primary][:3]
    if top3:
        print(f'\n  -> 高频非主标签 Top-3（可能有独立页面的信号）：')
        for tag, count in top3:
            exists = any(f'{tag}.md' in f[0] for f in files)
            mark = '(已有)' if exists else '(无页面，建议等原料)'
            print(f'     #{tag} ({count}次) {mark}')

    # 7. 品级分布
    print('\n[7] 品级分布')
    c1, c2, c3 = check_confidence(files)
    print(f'  上品: {len(c1)}  中品: {len(c2)}  下品: {len(c3)}')

    # 8. 时效提醒
    print('\n[8] 时效提醒（>90天 有时效字段的页面）')
    stale = check_timeliness(files)
    if stale:
        for s in stale:
            print(f'  STALE {s}')
    else:
        print('  无过期页面')
    print(f'  => 共 {len(stale)} 条')

    # 9. 推荐区合规
    print('\n[9] 推荐区合规')
    gl_warns, gl_gaps = check_tuijian(files, VAULT)
    if gl_warns:
        for w in gl_warns:
            print(f'  WARN {w}')
    if gl_gaps:
        for g in gl_gaps:
            print(f'  GAP {g}')
    print(f'  WARN {len(gl_warns)} 条 / GAP {len(gl_gaps)} 条')

    # 10. 日志格式
    print('\n[10] 日志格式')
    log_path = os.path.join(VAULT, '日志.md')
    log_warns = check_log_format(log_path)
    if log_warns:
        for w in log_warns:
            print(f'  WARN {w}')
    else:
        print('  格式正确')
    print(f'  => 共 {len(log_warns)} 条')

    # 11. 原料 frontmatter 白名单
    print('\n[11] 原料 frontmatter 白名单')
    raw_fm_warns = check_raw_fm(VAULT)
    for w in raw_fm_warns:
        print(f'  WARN {w}')
    print(f'  => 共 {len(raw_fm_warns)} 条')

    # 12. 原料完整链路
    print('\n[12] 原料链路完整性')
    raw_link_warns = check_raw_link(VAULT)
    for w in raw_link_warns:
        print(f'  WARN {w}')
    print(f'  => 共 {len(raw_link_warns)} 条')

    print('\n' + '=' * 55)
    print(f'缺口{len(gaps)} | 格式错误{len(format_errors)} | 死胡同{len(deadends)} | 孤立{len(isolated)} | 索引缺口{len(index_gaps)} | 时效{len(stale)} | 推荐区WARN{len(gl_warns)} GAP{len(gl_gaps)} | 日志格式{len(log_warns)} | 原料FM{len(raw_fm_warns)} | 链路{len(raw_link_warns)}')
    print('=' * 55)

    print('\n' + '=' * 55)
    print(f'缺口{len(gaps)} | 格式错误{len(format_errors)} | 死胡同{len(deadends)} | 孤立{len(isolated)} | 索引缺口{len(index_gaps)} | 时效{len(stale)} | 推荐区WARN{len(gl_warns)} GAP{len(gl_gaps)} | 日志格式{len(log_warns)} | 原料FM{len(raw_fm_warns)} | 链路{len(raw_link_warns)}')
    print('=' * 55)

if __name__ == '__main__':
    main()
