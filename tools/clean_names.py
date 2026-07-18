# -*- coding: utf-8 -*-
"""全站清洗：去掉 5+2 提法（统一 18维度），删除视频平台与其博主/机构名称及链接。"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONTENT = Path(__file__).parent.parent / "content"

RULES = [
    # ── 5+2 → 18维度 ──
    (r"[（(]5\+2\s*框架[）)]", ""),
    (r"5\+2\s*分析法", "18维度分析法"),
    (r"5\+2\s*分析结构", "18维度分析框架"),
    (r"5\+2\s*(框架|结构)", "18维度框架"),
    (r"5\+2", "18维度"),
    # ── 平台/博主链接与视频ID ──
    (r"https?://[^\s)\]>」』】]*(?:bilibili|b23\.tv|youtube|youtu\.be|jdbinvesting)[^\s)\]>」』】]*", ""),
    (r"\bBV[0-9A-Za-z]{9,12}\b", ""),
    # ── 博主/机构名 ──
    (r"美投君", ""),
    (r"美投(?![资入])", ""),
    (r"JDB\s*Investing", ""),
    (r"jdbinvesting", ""),
    (r"\bJDB\b", ""),
    (r"TOFU\s*版块", "专栏"),
    (r"\bTOFU\b", "专栏"),
    (r"荒野芯片半导体[｜|]", ""),
    (r"荒野芯片半导体", "芯片半导体系列"),
    (r"荒野", ""),
    (r"硅谷101", ""),
    # ── 平台名 ──
    (r"[Bb]站", ""),
    (r"[Bb]ilibili", ""),
    (r"[Yy]ou[Tt]ube", ""),
    (r"油管", ""),
    # ── 清理残留 ──
    (r"^title:\s*[｜|·\-—:：\s]+", "title: ", ),
]

def clean_text(t):
    for pat, rep in RULES:
        t = re.sub(pat, rep, t, flags=re.M)
    # 收尾：孤立分隔符、多余空格
    t = re.sub(r"^(title:\s*)[｜|·\s]+", r"\1", t, flags=re.M)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"^(#{1,6}\s*)[｜|·\s]+", r"\1", t, flags=re.M)
    return t

changed = 0
for f in CONTENT.rglob("*.md"):
    orig = f.read_text(encoding="utf-8")
    new = clean_text(orig)
    # 文件名去品牌
    newname = f.name
    for a, b in [("jdb-investing-", ""), ("jdb-", ""), ("huangye-", "")]:
        newname = newname.replace(a, b)
    target = f.with_name(newname)
    if new != orig or target != f:
        target.write_text(new, encoding="utf-8")
        if target != f:
            f.unlink()
        changed += 1
        # 打印标题变化
        m = re.search(r"^title:\s*(.+)$", new, re.M)
        print(f"  ~ {target.name}  ->  {m.group(1)[:60] if m else '?'}")
print(f"\ncleaned {changed} files")

# 校验：不应再出现的词
bad = []
for f in CONTENT.rglob("*.md"):
    t = f.read_text(encoding="utf-8")
    for w in ["5+2", "B站", "YouTube", "bilibili", "美投", "jdbinvesting", "JDB", "荒野", "硅谷101", "TOFU"]:
        if w in t:
            bad.append(f"{f.name}: {w}")
if bad:
    print("REMAINING:")
    for b in bad[:20]:
        print("  !", b)
else:
    print("verify OK: no banned names remain")
