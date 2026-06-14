#!/usr/bin/env python3
"""
语义关联扫描 — 灵台 Phase 1 语义探针
基于 bge-small-zh-v1.5 本地模型，扫描丹房页面间的语义相似度。

用法：
  python .workbuddy/scripts/semantic_scan.py                       # 全库扫描
  python .workbuddy/scripts/semantic_scan.py --threshold 0.7       # 自定义阈值
  python .workbuddy/scripts/semantic_scan.py --page "词典/含人量"  # 单页扫描
  python .workbuddy/scripts/semantic_scan.py --new-page "词典/xxx" # Ingest 用，输出 JSON
"""
import os
import sys
import json
import argparse
import numpy as np

VAULT = r"灵台"
DANFANG = os.path.join(VAULT, "丹房")
THRESHOLD = 0.75
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".workbuddy", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "embeddings_cache.json")
PYTHON_SEMANTIC = r"C:\Users\39029\.workbuddy\binaries\python\envs\semantic\Scripts\python.exe"


def find_md_files(root):
    """Find all .md files in the vault (excluding raw/, .git/, hidden dirs)."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden dirs, raw/, .git/
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ('原料', '原始资源')]
        for fn in filenames:
            if fn.endswith('.md') and not fn.startswith('.'):
                rel = os.path.relpath(os.path.join(dirpath, fn), VAULT)
                files.append((rel, os.path.join(dirpath, fn)))
    return files


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def embed_texts(texts):
    """Embed texts using local model (direct import since we run in semantic venv)."""
    import os
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    from sentence_transformers import SentenceTransformer
    try:
        model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    except:
        # Fallback: download cache may exist
        import sys
        sys.path.insert(0, r'C:\Users\39029\.cache\huggingface\hub')
        model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    emb = model.encode(texts, show_progress_bar=False)
    return emb.tolist()


def get_page_text(files, max_files=None):
    """Extract title + first 500 chars for embedding."""
    texts = []
    paths = []
    for i, (rel, abspath) in enumerate(files):
        if max_files and i >= max_files:
            break
        try:
            with open(abspath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        
        # Extract title from frontmatter or filename
        title = os.path.splitext(os.path.basename(rel))[0]
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                fm = content[3:end]
                for line in fm.split('\n'):
                    if line.strip().startswith('标题:'):
                        title = line.split(':', 1)[1].strip()
                        break
        
        # Clean wikilinks
        import re
        clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', content)
        clean = re.sub(r'<img[^>]+>', '', clean)
        
        texts.append(f"{title}. {clean[:500]}")
        paths.append(rel)
    
    return texts, paths


def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def is_cross_platform_version(path1, path2):
    """Check if two files are cross-platform versions of the same content."""
    # Normalize paths
    p1 = path1.replace('\\', '/').replace('.md', '')
    p2 = path2.replace('\\', '/').replace('.md', '')
    
    # Extract filename (without directory)
    name1 = p1.split('/')[-1]
    name2 = p2.split('/')[-1]
    
    # Same filename = cross-platform version
    if name1 == name2:
        return True
    
    # Check if filenames are similar (e.g., "6天搭建AI知识引擎" in both)
    # by removing common prefixes/suffixes
    return False


def scan_all(threshold=THRESHOLD, page_filter=None):
    print(f"🔍 Scanning 丹房 with threshold={threshold}...")
    
    files = find_md_files(DANFANG)
    print(f"   Found {len(files)} files")
    
    if page_filter:
        files = [(r, p) for r, p in files if page_filter in r]
        if not files:
            print(f"   No files matching '{page_filter}'")
            return
        print(f"   Filtered to {len(files)} files matching '{page_filter}'")
    
    texts, paths = get_page_text(files)
    print(f"   Generating embeddings for {len(texts)} pages...")
    
    cache = load_cache()
    uncached_texts = []
    uncached_indices = []
    for i, (text, path) in enumerate(zip(texts, paths)):
        if path not in cache:
            uncached_texts.append(text)
            uncached_indices.append(i)
    
    if uncached_texts:
        print(f"   New pages to embed: {len(uncached_texts)}")
        new_embs = embed_texts(uncached_texts)
        if new_embs is None:
            print("   ❌ Embedding failed")
            return
        for idx, emb in zip(uncached_indices, new_embs):
            cache[paths[idx]] = emb
        save_cache(cache)
    
    # Build embedding matrix
    embeddings = np.array([cache[p] for p in paths])
    n = len(paths)
    
    # Find existing links
    existing_links = set()
    for rel, abspath in files:
        try:
            with open(abspath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        import re
        for match in re.finditer(r'\[\[([^\]]+?)(?:\||\])', content):
            target = match.group(1).strip()
            if target.startswith('丹房/'):
                existing_links.add((rel, target))
    
    # Scan
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = cosine_sim(embeddings[i], embeddings[j])
            if sim >= threshold:
                # Check if already linked
                already_linked = False
                for a, b in [(paths[i], paths[j]), (paths[j], paths[i])]:
                    # Check both directions
                    a_key = a.replace('\\', '/').replace('.md', '')
                    b_key = b.replace('\\', '/').replace('.md', '')
                    # Wikilink formats: [[丹房/...]], [[丹房/...|text]]
                    for (src, tgt) in existing_links:
                        src_norm = src.replace('\\', '/').replace('.md', '')
                        tgt_norm = tgt.replace('\\', '/').replace('.md', '')
                        if a_key == src_norm and b_key == tgt_norm:
                            already_linked = True
                            break
                    if already_linked:
                        break
                
                if not already_linked:
                    # Check if cross-platform version
                    if not is_cross_platform_version(paths[i], paths[j]):
                        pairs.append((sim, paths[i], paths[j]))
    
    # Sort by similarity
    pairs.sort(key=lambda x: -x[0])
    
    print(f"\n{'='*60}")
    print(f"📊 未关联的高相似度页面对 ({len(pairs)} pairs ≥ {threshold})")
    print(f"{'='*60}")
    
    for sim, p1, p2 in pairs[:30]:
        p1_short = p1.replace('丹房/', '').replace('.md', '')
        p2_short = p2.replace('丹房/', '').replace('.md', '')
        bar_len = int(sim * 30)
        bar = '█' * bar_len + '░' * (30 - bar_len)
        print(f"  {sim:.3f} {bar}  {p1_short}  ↔  {p2_short}")
    
    if len(pairs) > 30:
        print(f"  ... and {len(pairs) - 30} more pairs")
    
    print(f"\n✅ Total pairs found: {len(pairs)}")
    return pairs


def scan_new_page(page_path, threshold=THRESHOLD):
    """Scan a single new page against the cached corpus. Returns JSON for Ingest."""
    import re
    
    # Normalize path separators for Windows
    page_path = page_path.replace('/', os.sep).replace('\\', os.sep)
    abs_path = os.path.join(VAULT, page_path)
    # Add .md extension if not present
    if not abs_path.endswith('.md'):
        abs_path += '.md'
    if not os.path.exists(abs_path):
        return json.dumps({"error": f"Page not found: {page_path}"}, ensure_ascii=False)
    
    # Read page content
    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    title = os.path.splitext(os.path.basename(page_path))[0]
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            fm = content[3:end]
            for line in fm.split('\n'):
                if line.strip().startswith('标题:'):
                    title = line.split(':', 1)[1].strip()
                    break
    
    clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', content)
    clean = re.sub(r'<img[^>]+>', '', clean)
    page_text = f"{title}. {clean[:500]}"
    
    # Load cache
    cache = load_cache()
    if not cache:
        # First time: do full scan first
        return json.dumps({"error": "No cache. Run full scan first."}, ensure_ascii=False)
    
    # Embed new page
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    new_emb = model.encode([page_text], show_progress_bar=False)[0]
    
    # Save to cache
    cache[page_path] = new_emb.tolist()
    save_cache(cache)
    
    # Compare against all cached pages
    pairs = []
    for cached_path, cached_emb in cache.items():
        if cached_path == page_path:
            continue
        sim = cosine_sim(new_emb, np.array(cached_emb))
        if sim >= threshold:
            # Check if already linked
            already = False
            for match in re.finditer(r'\[\[([^\]]+?)(?:\||\])', content):
                target = match.group(1).strip()
                # Normalize both paths
                target_norm = target.replace('\\', '/')
                cached_norm = cached_path.replace('\\', '/')
                if cached_norm == target_norm or cached_norm.replace('.md', '') == target_norm:
                    already = True
                    break
            if not already:
                pairs.append({
                    "similarity": round(sim, 4),
                    "page": cached_path,
                    "display": cached_path.replace('丹房/', '').replace('.md', '')
                })
    
    pairs.sort(key=lambda x: -x["similarity"])
    
    result = {
        "source": page_path,
        "source_display": page_path.replace('丹房/', '').replace('.md', ''),
        "threshold": threshold,
        "pairs": pairs[:10],  # Top 10
        "total": len(pairs)
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Semantic scan for 灵台")
    parser.add_argument('--threshold', type=float, default=THRESHOLD, help='Similarity threshold (0-1)')
    parser.add_argument('--page', type=str, default=None, help='Scan a specific page (human readable)')
    parser.add_argument('--new-page', type=str, default=None, help='New page path for Ingest (JSON output)')
    parser.add_argument('--json', action='store_true', help='JSON output mode (for Ingest integration)')
    args = parser.parse_args()
    
    if args.new_page:
        result = scan_new_page(args.new_page, args.threshold)
        print(result)
        return
    
    pairs = scan_all(threshold=args.threshold, page_filter=args.page)
    
    if args.json and pairs:
        json_pairs = [{"similarity": round(s, 4), "page_a": p1.replace('\\', '/'), "page_b": p2.replace('\\', '/')} for s, p1, p2 in pairs]
        print(json.dumps({"total": len(json_pairs), "threshold": args.threshold, "pairs": json_pairs[:30]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
