# -*- coding: utf-8 -*-
"""把 Gmail 草稿箱近3个月金融投资内容分类导入飘投资网站 content/。
规则：新闻类跳过；个人隐私跳过；空正文跳过；系列流水合并为合集；不确定→history。"""
import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOOLDIR = r"C:\Users\xupia\.claude\projects\g--gs\9bcb6c0d-33e0-4044-ab3d-27539ed0c9ae\tool-results"
CONTENT = Path(r"g:\gs\p-investing\content")

def fix_mojibake(t):
    if not t:
        return t
    if re.search(r"[àâäåæçèéêëìîïðñòóôõö]{2}", t, re.I) or "â" in t or "ï¼" in t:
        try:
            f = t.encode("latin-1").decode("utf-8")
            if re.search(r"[一-鿿]", f):
                return f
        except Exception:
            pass
    return t

# ── 读取全部草稿 ──
drafts = []
seen_ids = set()
for f in sorted(glob.glob(TOOLDIR + r"\mcp-claude_ai_Gmail-list_drafts-*.txt")):
    d = json.load(open(f, encoding="utf-8"))
    for dr in d.get("drafts", []):
        m = dr.get("message", dr)
        mid = m.get("id")
        if mid in seen_ids:
            continue
        seen_ids.add(mid)
        drafts.append({
            "subject": fix_mojibake(m.get("subject", "")).strip(),
            "date": (m.get("date", "") or "")[:10],
            "body": m.get("plaintextBody") or "",
        })
print(f"loaded drafts: {len(drafts)}")

# ── 跳过规则 ──
SKIP_PATTERNS = [
    r"^\[News Daily",              # 新闻总结（用户指定不要）
    r"^美投君每日报告",              # 每日新闻类
    r"^Daily Financial News",
]
PRIVATE_PATTERNS = [               # 个人隐私/无关文件摘要
    r"收入证明", r"客户资料", r"Client Information", r"资产证明", r"Asset Certificate",
    r"工商银行历史明细", r"白皮书", r"弘达", r"常湘", r"马晓立",
    r"- 092 - b003d220", r"C8-99A4", r"20260617095532",
]

# ── 系列合并定义: (匹配正则, slug, 分类, 标题, 标签) ──
SERIES = [
    (r"^WeChat File Transfer Summary 2026-06-17", "reports-2026-06-17-wechat", "history",
     "投行研报摘要合集（2026-06-17 微信批次，50篇）", "研报合集, 高盛"),
    (r"^File Transfer PDF Summary 2026-06-21", "reports-2026-06-21-batch", "history",
     "投行研报摘要合集（2026-06-21 批次，12篇：FOMC/宏观/科技）", "研报合集, 高盛, FOMC"),
    (r"^WeChat PDF Summary 2026-06-1[14]", "reports-2026-06-11-wechat", "history",
     "投行研报摘要合集（2026-06-11 微信批次，79篇）", "研报合集, 高盛"),
    (r"^WeChat After 11:25 Summary 2026-06-04", "reports-2026-06-04-batch", "history",
     "投行研报摘要合集（2026-06-04 批次，30篇）", "研报合集"),
    (r"^Current 181 PDF Summary", "reports-2026-05-26-current181", "history",
     "投行研报摘要合集（2026-05-26 Current 181 系列，105篇）", "研报合集, 高盛, 大摩"),
    (r"^Current 49 PDF Summary", "reports-2026-05-26-current49", "history",
     "投行研报摘要合集（2026-05-26 Current 49 系列，21篇）", "研报合集"),
    (r"^Selected PDF Summary 2026-05-26", "reports-2026-05-26-selected", "history",
     "投行研报摘要合集（2026-05-26 Selected 系列，35篇）", "研报合集"),
    (r"^PDF Summary 2026-05-26", "reports-2026-05-26-pdf", "history",
     "投行研报摘要合集（2026-05-26 PDF 系列，17篇）", "研报合集"),
    (r"^【PDF总结 \d+/51】|^2026-05-24 微信文件传输助手 51份", "reports-2026-05-24-batch51", "history",
     "投行研报摘要合集（2026-05-24 微信批次，51篇）", "研报合集"),
    (r"^(SemiAnalysis Recent 20 Summary|20 Summary 2026-06-13)", "semianalysis-20-2026-06", "industries",
     "SemiAnalysis 最近20篇文章深度总结（2026-06-13）", "SemiAnalysis, AI芯片, 数据中心"),
    (r"^PDD (Individual|Local) Research", "pdd-research-2026-06", "companies",
     "拼多多 PDD 研报与本地研究合集（15篇，2024-2026 财报与 Temu 专题）", "PDD, 电商, 中概股"),
    (r"^HOOD (Individual Research|本地研报)", "hood-research-2026-06", "companies",
     "Robinhood HOOD 研报与本地研究合集（7篇）", "HOOD, 券商, 加密"),
    (r"^荒野芯片半导体｜第\d+集", "huangye-chip-series-43", "industries",
     "荒野芯片半导体系列 43 集完整总结（HBM/CoWoS/TPU/GPU架构/先进封装）", "半导体, HBM, 先进封装, TPU, GPU"),
]

# ── 单篇分类规则: (匹配正则, 分类) ──
SINGLE_RULES = [
    (r"18维深度研究|18维度深度分析|Deep Research|机构级深度研究|量子横向对比|TSLA专题|康宁GlassBridge", "companies"),
    (r"AI产业链超级深度|电力能源.*视频|AI电力能源|半导体产业链未来机会|光互联与玻璃基板|B站AI产业链|中国半导体材料|MLCC到铟|Watts, Wafers|荒野芯片半导体合集", "industries"),
    (r"FCN结构化产品", "options"),
    (r"宏观|All-In Podcast|Gavin Baker访谈|Generating Alpha|Serenity|aleabitoreddit|13F|WhaleWisdom|ETF配置|TOFU 版块|WallStreetBets|transurf|JDB 每日报告|去全球化", "macro"),
    (r"B站全球历史|Poker Theory", "history"),
]

def classify_single(subject):
    for pat, cat in SINGLE_RULES:
        if re.search(pat, subject):
            return cat
    return "history"   # 不确定 → 历史（用户指定）

def slugify(s, fallback):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    s = re.sub(r"-{2,}", "-", s)
    return (s[:50].strip("-") or fallback)

def clean_reply_quote(body):
    """清洗回复式草稿：去掉引用前缀和邮件头。"""
    lines = body.splitlines()
    out = []
    for ln in lines:
        if re.match(r"^On .{5,60} wrote:\s*$", ln) or ln.strip() in ("哦。",):
            continue
        out.append(re.sub(r"^>\s?", "", ln))
    return "\n".join(out).strip()

series_items = defaultdict(list)
singles, skipped_news, skipped_private, skipped_empty, skipped_tiny = [], [], [], [], []

for d in drafts:
    subj, body = d["subject"], d["body"]
    if any(re.search(p, subj) for p in SKIP_PATTERNS):
        skipped_news.append(subj); continue
    if any(re.search(p, subj) for p in PRIVATE_PATTERNS):
        skipped_private.append(subj); continue
    if not body.strip():
        skipped_empty.append(subj); continue
    if subj.startswith("荒野芯片半导体合集"):
        continue  # 单集合并版已覆盖，避免重复
    matched = False
    for pat, slug, cat, title, tags in SERIES:
        if re.search(pat, subj):
            series_items[(slug, cat, title, tags)].append(d)
            matched = True
            break
    if matched:
        continue
    body_fixed = fix_mojibake(body)
    if subj.startswith("Re:"):
        body_fixed = clean_reply_quote(body_fixed)
        m = re.search(r"^#\s*(.+)$", body_fixed, re.M)
        if m:
            subj = m.group(1).strip()
    if len(body_fixed) < 400:
        skipped_tiny.append(f"{subj} ({len(body_fixed)}字)")
        continue
    singles.append({"subject": subj, "date": d["date"], "body": body_fixed})

# ── 写单篇 ──
written = []
used_names = set()
def write_md(cat, date, title, tags, body, slug):
    p = CONTENT / cat / f"{date}-{slug}.md"
    n = 2
    while p.name in used_names or p.exists():
        p = CONTENT / cat / f"{date}-{slug}-{n}.md"; n += 1
    used_names.add(p.name)
    title = title.replace("\n", " ").strip()
    fm = f"---\ntitle: {title}\ncategory: {cat}\ndate: {date}\ntags: {tags}\nsource: gmail-draft\n---\n\n"
    p.write_text(fm + body.strip() + "\n", encoding="utf-8")
    written.append((cat, p.name))

TICKER_RE = re.compile(r"\b([A-Z]{2,5})\b")
KNOWN_TICKERS = {"RKLB","HWM","NBIS","QUBT","QBTS","RGTI","IONQ","AVAV","NVDA","TSLA","STM","PDD","HOOD","FCN","ETF","WSB","SPY","QQQ","SOXX","SMH","GRID","CBOE"}

for s in singles:
    cat = classify_single(s["subject"])
    tickers = sorted(set(TICKER_RE.findall(s["subject"])) & KNOWN_TICKERS - {"FCN","ETF","WSB"})
    tags = "邮件存档" + ("," + ",".join(tickers) if tickers else "")
    fallback = "note"
    slug = slugify(s["subject"], fallback)
    title = re.sub(r"\s*[-—|｜]\s*2026[-.\d]*\s*$", "", s["subject"])
    fm_extra = f"tickers: {', '.join(tickers)}\n" if tickers else ""
    p = CONTENT / cat / f"{s['date']}-{slug}.md"
    n = 2
    while p.name in used_names or p.exists():
        p = CONTENT / cat / f"{s['date']}-{slug}-{n}.md"; n += 1
    used_names.add(p.name)
    fm = f"---\ntitle: {title}\ncategory: {cat}\ndate: {s['date']}\n{fm_extra}tags: {tags}\nsource: gmail-draft\n---\n\n"
    p.write_text(fm + s["body"].strip() + "\n", encoding="utf-8")
    written.append((cat, p.name))

# ── 写合集 ──
def item_sort_key(d):
    m = re.search(r"(\d{1,3})\s*/?\d*\s*[-】]", d["subject"][::-1])
    m2 = re.search(r"- (\d{2,3}) -|第(\d+)集|(\d+)/51】| - (\d{2}) - ", d["subject"])
    if m2:
        for g in m2.groups():
            if g:
                return int(g)
    return 999

for (slug, cat, title, tags), items in series_items.items():
    items.sort(key=item_sort_key)
    date = max(i["date"] for i in items)
    parts = []
    for it in items:
        sub = it["subject"]
        sub = re.sub(r"^(WeChat File Transfer Summary|File Transfer PDF Summary|WeChat PDF Summary|WeChat After 11:25 Summary|Current \d+ PDF Summary|Selected PDF Summary|PDF Summary|SemiAnalysis Recent 20 Summary|20 Summary|PDD Individual Research Analysis|HOOD Individual Research Analysis|【PDF总结)\s*[\d/】\s-]*[-\s]*", "", sub)
        sub = re.sub(r"^\d{4}-\d{2}-\d{2}\s*-\s*\d+\s*-\s*", "", sub) or it["subject"]
        parts.append(f"## {sub}\n\n{fix_mojibake(it['body']).strip()}")
    body = f"> 本合集由 {len(items)} 篇邮件草稿摘要合并而成，可用页内搜索定位。\n\n" + "\n\n---\n\n".join(parts)
    fm = f"---\ntitle: {title}\ncategory: {cat}\ndate: {date}\ntags: {tags}\nsource: gmail-draft\n---\n\n"
    p = CONTENT / cat / f"{date}-{slug}.md"
    p.write_text(fm + body + "\n", encoding="utf-8")
    written.append((cat, f"{p.name} ({len(items)}篇合并)"))

# ── 报告 ──
from collections import Counter
print("\n=== 写入统计 ===")
for cat, n in Counter(c for c, _ in written).items():
    print(f"  {cat}: {n} 个文件")
print(f"  合计 {len(written)} 个文件")
print(f"\n跳过: 新闻类 {len(skipped_news)} | 隐私 {len(skipped_private)} | 空正文 {len(skipped_empty)} | 过短 {len(skipped_tiny)}")
print("\n=== 空正文草稿（无法导入，如需要请重新生成）===")
for s in sorted(set(skipped_empty)):
    print("  -", s[:70])
print("\n=== 过短跳过 ===")
for s in skipped_tiny:
    print("  -", s[:70])
print("\n=== 隐私跳过 ===")
for s in skipped_private:
    print("  -", s[:60])
