# -*- coding: utf-8 -*-
"""
build.py — 把 content/ 下所有 Markdown 研究笔记编译成 docs/data.json，
并更新 service worker 缓存版本号，使手机端 PWA 下次联网时自动拉取新内容。

用法:  python build.py
无第三方依赖（frontmatter 用内置的迷你解析器）。
"""
import json
import re
import sys
import time
from pathlib import Path

# Windows 控制台默认 cp1252/gbk，中文输出会崩
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
DOCS = ROOT / "docs"

CATEGORIES = ["companies", "industries", "options", "macro", "reports", "history"]

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text):
    """解析 md 开头的 --- 块。支持 key: value、[a, b] 列表和逗号分隔列表。"""
    m = FM_RE.match(text)
    if not m:
        return None, text
    meta = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip().strip('"').strip("'")
        if key in ("tickers", "tags"):
            val = val.strip("[]")
            items = [v.strip().strip('"').strip("'") for v in val.split(",")]
            meta[key] = [v for v in items if v]
        else:
            meta[key] = val
    return meta, text[m.end():]


def excerpt(body, limit=160):
    """去掉 markdown 语法取纯文本摘要。"""
    t = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*_`>|#-]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def build():
    entries = []
    errors = []
    for cat in CATEGORIES:
        d = CONTENT / cat
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            text = f.read_text(encoding="utf-8-sig")
            meta, body = parse_frontmatter(text)
            if meta is None:
                errors.append(f"{f}: 缺少 frontmatter (--- 块)")
                continue
            if not meta.get("title"):
                errors.append(f"{f}: frontmatter 缺少 title")
                continue
            date = meta.get("date", "")
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                errors.append(f"{f}: date 需为 YYYY-MM-DD 格式, 当前: '{date}'")
                continue
            entries.append({
                "id": f"{cat}/{f.stem}",
                "category": cat,
                "title": meta["title"],
                "date": date,
                "tickers": meta.get("tickers", []),
                "tags": meta.get("tags", []),
                "source": meta.get("source", ""),
                "excerpt": excerpt(body),
                "body": body.strip(),
            })

    if errors:
        print("构建失败，以下文件有问题：")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    entries.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    version = time.strftime("%Y%m%d%H%M%S")
    data = {"version": version, "count": len(entries), "entries": entries}
    out = DOCS / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # 更新 service worker 缓存版本号，触发客户端更新
    sw = DOCS / "sw.js"
    if sw.exists():
        txt = sw.read_text(encoding="utf-8")
        txt = re.sub(r"const CACHE = 'pi-[^']*'", f"const CACHE = 'pi-{version}'", txt)
        sw.write_text(txt, encoding="utf-8")

    print(f"OK: {len(entries)} 篇笔记 -> {out}  (version {version})")
    by_cat = {}
    for e in entries:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    for cat in CATEGORIES:
        print(f"  {cat:<10} {by_cat.get(cat, 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
