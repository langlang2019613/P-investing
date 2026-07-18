# -*- coding: utf-8 -*-
"""修复 clean_names.py 的三个副作用：标题空格、GOOGL 文件中作为业务板块的 YouTube、残留 JDB。"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONTENT = Path(__file__).parent.parent / "content"

fixed = 0
for f in CONTENT.rglob("*.md"):
    t = f.read_text(encoding="utf-8")
    orig = t
    # 1) 恢复 markdown 标题与 frontmatter title 的空格
    t = re.sub(r"^(#{1,6})(?=[^#\s])", r"\1 ", t, flags=re.M)
    t = re.sub(r"^title:(?=\S)", "title: ", t, flags=re.M)
    # 2) 残留品牌与重复词
    t = t.replace("JDB", "")
    t = t.replace("芯片半导体系列系列", "芯片半导体系列")
    t = re.sub(r"^title:\s+", "title: ", t, flags=re.M)
    if t != orig:
        f.write_text(t, encoding="utf-8")
        fixed += 1
print(f"fixed {fixed} files")

# 3) GOOGL 深度分析：恢复作为 Alphabet 业务板块的 YouTube
g = CONTENT / "companies" / "2026-07-19-googl-deep-dive-5plus2.md"
t = g.read_text(encoding="utf-8")
repl = [
    ("分发入口 Search/Android/ + 云", "分发入口 Search/Android/YouTube + 云"),
    ("全球第一（Search+ 约 27-28% 份额）", "全球第一（Search+YouTube 约 27-28% 份额）"),
    ("| 广告 | ~$9.5B | +11% | 订阅增速已超广告 |", "| YouTube 广告 | ~$9.5B | +11% | 订阅增速已超广告 |"),
    ("付费订阅数达 **3.5 亿**（+Google One 驱动）", "付费订阅数达 **3.5 亿**（YouTube+Google One 驱动）"),
    ("Android 30亿设备、Chrome、）", "Android 30亿设备、Chrome、YouTube）"),
    ("Android/Chrome//Gmail/Maps 六个", "Android/Chrome/YouTube/Gmail/Maps 六个"),
    ("历史并购：/DeepMind/Android", "历史并购：YouTube/DeepMind/Android"),
    ("广告业务（Search+）：~$2.5T", "广告业务（Search+YouTube）：~$2.5T"),
]
n = 0
for a, b in repl:
    if a in t:
        t = t.replace(a, b); n += 1
g.write_text(t, encoding="utf-8")
print(f"GOOGL restored {n}/{len(repl)} spots")

# 4) 终检
bad = []
for f in CONTENT.rglob("*.md"):
    t = f.read_text(encoding="utf-8")
    if re.search(r"5\+2", t): bad.append(f"{f.name}: 5+2")
    if re.search(r"[Bb]站|bilibili", t): bad.append(f"{f.name}: B站")
    if re.search(r"(?<![欧中])美投", t): bad.append(f"{f.name}: 美投")
    if re.search(r"JDB|jdbinvesting|荒野|硅谷101|TOFU", t): bad.append(f"{f.name}: 品牌残留")
    if f.name != "2026-07-19-googl-deep-dive-5plus2.md" and re.search(r"[Yy]ou[Tt]ube", t):
        bad.append(f"{f.name}: YouTube")
    if re.search(r"^#{1,6}[^#\s]", t, re.M): bad.append(f"{f.name}: 标题缺空格")
print("REMAINING ISSUES:" if bad else "verify OK")
for b in bad[:20]:
    print("  !", b)
