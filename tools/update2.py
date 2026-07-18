# -*- coding: utf-8 -*-
"""更新2：① 去掉全站「视频」相关字样；② 研报合集移入新栏目 reports。"""
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONTENT = Path(__file__).parent.parent / "content"
(CONTENT / "reports").mkdir(exist_ok=True)

# ── ① 视频字样清理（顺序敏感）──
WORD_RULES = [
    ("本视频", "本篇"), ("该视频", "该篇"), ("这个视频", "本篇"), ("整条视频", "全篇"),
    ("部视频", "篇"), ("条视频", "篇"), ("个视频", "篇"), ("集视频", "集"),
    ("视频资料库", "资料库"), ("视频内容重做版", "内容重做版"),
    ("视频详细总结", "详细总结"), ("视频深度总结", "深度总结"), ("视频总结", "总结"),
    ("视频详解", "详解"), ("视频整理", "整理"), ("视频合集", "合集"),
    ("视频", ""),  # 兜底
]

def clean(t):
    for a, b in WORD_RULES:
        t = t.replace(a, b)
    t = re.sub(r"^title:\s*[｜|：:·\s]+", "title: ", t, flags=re.M)
    t = re.sub(r"(title: .*?)[｜|：:·]\s*$", r"\1", t, flags=re.M)
    return t

changed = 0
for f in list(CONTENT.rglob("*.md")):
    t = f.read_text(encoding="utf-8")
    new = clean(t)
    if new != t:
        f.write_text(new, encoding="utf-8")
        changed += 1
print(f"视频字样清理: {changed} 个文件")

# ── ② 研报合集 → reports 栏目 ──
moved = []
for f in list((CONTENT / "history").glob("*.md")):
    t = f.read_text(encoding="utf-8")
    m = re.search(r"^title:\s*(.+)$", t, re.M)
    title = m.group(1) if m else ""
    if "研报摘要合集" in title or "PDF 详细摘要" in title or "reports-" in f.name:
        t = re.sub(r"^category:\s*history\s*$", "category: reports", t, flags=re.M)
        target = CONTENT / "reports" / f.name
        target.write_text(t, encoding="utf-8")
        f.unlink()
        moved.append(f.name)
print(f"移入研报分析: {len(moved)} 篇")
for n in moved:
    print("  ->", n)

# ── 校验 ──
bad = []
for f in CONTENT.rglob("*.md"):
    t = f.read_text(encoding="utf-8")
    if "视频" in t:
        bad.append(f.name)
print("残留「视频」:", bad if bad else "无")
