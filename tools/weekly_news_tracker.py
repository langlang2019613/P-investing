#!/usr/bin/env python3
"""Collect the public metadata of P-Investing's weekly reading sources.

The tracker intentionally stores titles, links and short public excerpts rather
than copying full articles. RSS/Atom is preferred. Sources without a usable feed
fall back to their public index page, and every failure is exposed in the output.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, deque
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "tools" / "weekly_news_sources.json"
HISTORY_PATH = ROOT / "data" / "weekly_news" / "history.json"
OUTPUT_PATH = ROOT / "docs" / "news_tracker.json"
USER_AGENT = "P-investing-weekly-news/1.0 research@pickalphas.com"
TIMEOUT = 24

TAGS: dict[str, tuple[str, ...]] = {
    "AI模型": ("artificial intelligence", " ai ", "llm", "language model", "foundation model", "agentic", "inference", "training model"),
    "算力/芯片": ("semiconductor", "chip", "gpu", "accelerator", "compute", "processor", "cpu", "nvidia", "amd", "intel"),
    "HBM/存储": ("hbm", "dram", "nand", "memory", "micron", "sk hynix"),
    "先进封装": ("cowos", "chiplet", "advanced packaging", "2.5d", "3d packaging"),
    "半导体制造": ("foundry", "wafer", "lithography", "euv", "fab ", "tsmc", "samsung", "process node", "transistor"),
    "云/数据中心": ("data center", "datacenter", "cloud", "hyperscaler", "server", "aws", "azure"),
    "能源/电网": ("energy", "electricity", "power grid", "grid", "nuclear", "solar", "battery", "storage", "megawatt", "gas turbine"),
    "中国科技": ("china", "chinese", "beijing", "shenzhen", "deepseek", "alibaba", "tencent", "bytedance"),
    "亚洲供应链": ("taiwan", "korea", "japan", "asia", "supply chain", "tsmc", "samsung", "hynix"),
    "创投/融资": ("venture", "funding", "series a", "series b", "series c", "valuation", "startup", "investment"),
    "企业软件": ("saas", "enterprise software", "enterprise ai", "cloud software", "arr", "go-to-market", "gtm"),
    "生物科技": ("biotech", "drug", "clinical", "therapeutic", "pharma", "fda", "trial", "molecule"),
    "长寿": ("longevity", "aging", "ageing", "healthspan", "lifespan"),
    "政策/地缘": ("policy", "regulation", "geopolit", "tariff", "export control", "government", "national security"),
    "财报/估值": ("earnings", "revenue", "margin", "cash flow", "capex", "forecast", "outlook", "valuation"),
}

TICKERS: dict[str, tuple[str, ...]] = {
    "NVDA": ("nvidia",), "AMD": ("advanced micro devices", " amd "), "INTC": ("intel",),
    "TSM": ("tsmc", "taiwan semiconductor"), "MU": ("micron",), "ASML": ("asml",),
    "AVGO": ("broadcom",), "MRVL": ("marvell",), "MSFT": ("microsoft", "azure"),
    "GOOGL": ("google", "alphabet", "gemini"), "AMZN": ("amazon", "aws"),
    "META": ("meta", "facebook"), "AAPL": ("apple",), "TSLA": ("tesla",),
    "CEG": ("constellation energy",), "VRT": ("vertiv",),
}

CATEGORY_LENS = {
    "semiconductors": "关注产能、良率、先进封装、存储瓶颈与供应商议价权。",
    "venture": "关注资金流向、采用速度、竞争结构与商业模式的可持续性。",
    "ai_research": "区分研究能力进展、工程可用性、成本曲线与商业化证据。",
    "deep_analysis": "用于建立公司和产业长期框架，关键判断仍需回到一手数据。",
    "asia_supply": "关注亚洲供应链、政策变化、交付节奏与西方信息时差。",
    "energy": "关注并网进度、实际通电MW、电价、设备交付和监管约束。",
    "biotech": "关注临床阶段、试验终点、现金跑道、交易条款与监管风险。",
    "signals": "高频线索只作发现入口，需回到公司、论文或监管原始来源验证。",
}

SKIP_TITLES = {
    "home", "about", "archive", "articles", "insights", "news", "newsletter", "podcast",
    "podcasts", "learn more", "read more", "view all", "see all", "subscribe", "contact",
    "privacy", "terms", "team", "portfolio", "sign in", "log in", "the future",
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def fetch(url: str) -> tuple[bytes, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml,application/atom+xml,text/xml,text/html;q=0.9,*/*;q=0.5",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read(), response.geturl(), response.headers.get("Content-Type", "")


def clean_text(value: str | None, limit: int = 0) -> str:
    if not value:
        return ""
    value = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    if limit and len(value) > limit:
        value = value[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:，。；：") + "…"
    return value


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].rsplit(":", 1)[-1].lower()


def element_text(element: ET.Element, names: set[str]) -> str:
    for child in list(element):
        if local_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = clean_text(value)
    try:
        parsed = parsedate_to_datetime(value)
        if parsed:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def canonical_url(url: str, base: str = "") -> str:
    url = urllib.parse.urljoin(base, html.unescape(url.strip()))
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    blocked = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "source", "mc_cid", "mc_eid"}
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k.lower() not in blocked])
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))


def item_id(source_id: str, url: str, title: str) -> str:
    stable = url or re.sub(r"\W+", " ", title.lower()).strip()
    return hashlib.sha256(f"{source_id}|{stable}".encode("utf-8")).hexdigest()[:20]


def parse_feed(raw: bytes, source: dict[str, Any], feed: dict[str, str], final_url: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # A few legacy feeds emit bare ampersands or control bytes. Repair only
        # XML syntax; article text remains a short public excerpt.
        repaired = raw.decode("utf-8", errors="replace")
        repaired = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", repaired)
        repaired = re.sub(r"&(?!#\d+;|#x[0-9a-f]+;|[a-z][a-z0-9]+;)", "&amp;", repaired, flags=re.I)
        root = ET.fromstring(repaired)
    entries = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]
    output: list[dict[str, Any]] = []
    for entry in entries:
        title = clean_text(element_text(entry, {"title"}), 260)
        if not title:
            continue
        link = element_text(entry, {"link"})
        if not link:
            for child in list(entry):
                if local_name(child.tag) == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    if child.attrib.get("rel", "alternate") == "alternate":
                        break
        link = canonical_url(link or element_text(entry, {"guid", "id"}), final_url)
        if not link:
            continue
        published = parse_datetime(element_text(entry, {"pubdate", "published", "updated", "date", "created"}))
        summary = clean_text(element_text(entry, {"description", "summary", "content", "encoded"}), 460)
        output.append(make_item(source, title, link, published, summary, feed.get("channel", "RSS"), "feed"))
    return output


def parse_youtube_page(raw: bytes, source: dict[str, Any], feed: dict[str, str]) -> list[dict[str, Any]]:
    text = raw.decode("utf-8", errors="replace")
    patterns = [
        re.compile(r'"videoId":"(?P<id>[^"]+)".{0,5000}?"title":\{"runs":\[\{"text":"(?P<title>(?:\\.|[^"])*)"', re.S),
        re.compile(r'"videoId":"(?P<id>[^"]+)".{0,5000}?"metadata":\{"lockupMetadataViewModel":\{"title":\{"content":"(?P<title>(?:\\.|[^"])*)"', re.S),
    ]
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    matches = sorted((match for pattern in patterns for match in pattern.finditer(text)), key=lambda match: match.start())
    for match in matches:
        video_id = match.group("id")
        if video_id in seen:
            continue
        seen.add(video_id)
        try:
            title = json.loads(f'"{match.group("title")}"')
        except json.JSONDecodeError:
            title = match.group("title").replace(r'\"', '"')
        context = text[match.end():match.end() + 5000]
        relative_match = re.search(r'"publishedTimeText":\{"simpleText":"([^"]+)"', context)
        if not relative_match:
            relative_match = re.search(r'"text":\{"content":"((?:\d+\s+)?(?:minute|hour|day|week|month|year)s? ago)"', context, re.I)
        published: datetime | None = None
        if relative_match:
            label = relative_match.group(1)
            amount_match = re.match(r"(\d+)\s+(minute|hour|day|week|month|year)s? ago", label, re.I)
            if amount_match:
                amount = int(amount_match.group(1))
                unit = amount_match.group(2).lower()
                days = amount / 1440 if unit == "minute" else amount / 24 if unit == "hour" else amount if unit == "day" else amount * 7 if unit == "week" else amount * 30 if unit == "month" else amount * 365
                published = datetime.now(timezone.utc) - timedelta(days=days)
            else:
                published = parse_datetime(label)
        output.append(make_item(
            source, title, f"https://www.youtube.com/watch?v={video_id}", published, "",
            feed.get("channel", "YouTube"), "youtube_page",
        ))
        if len(output) >= 30:
            break
    return output


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self.recent: deque[str] = deque(maxlen=14)
        self.current: dict[str, Any] | None = None
        self.in_anchor = 0

    def _finish(self) -> None:
        if self.current:
            self.current["title"] = clean_text(" ".join(self.current["text"]), 300)
            self.current["context"] = clean_text(" ".join(self.current["before"] + self.current["after"]), 700)
            self.links.append(self.current)
        self.current = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag.lower() == "a" and attrs_dict.get("href"):
            self._finish()
            label = attrs_dict.get("aria-label") or attrs_dict.get("title") or ""
            self.current = {"href": attrs_dict["href"], "text": [label] if label else [], "before": list(self.recent), "after": []}
            self.in_anchor = 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.in_anchor:
            self.in_anchor = 0

    def handle_data(self, data: str) -> None:
        value = clean_text(data)
        if not value:
            return
        self.recent.append(value)
        if self.current:
            target = self.current["text"] if self.in_anchor else self.current["after"]
            if sum(len(x) for x in target) < 500:
                target.append(value)

    def close(self) -> None:
        super().close()
        self._finish()


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() != "meta":
            return
        key = (attrs_dict.get("property") or attrs_dict.get("name") or attrs_dict.get("itemprop") or "").lower()
        content = attrs_dict.get("content", "")
        if key and content and key not in self.meta:
            self.meta[key] = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def context_date(context: str) -> datetime | None:
    patterns = (
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2})\b",
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},\s+20\d{2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, context, flags=re.I)
        if match:
            return parse_datetime(match.group(1).replace("Sept.", "Sep").replace("Sep.", "Sep"))
    return None


def make_item(
    source: dict[str, Any], title: str, url: str, published: datetime | None,
    excerpt: str, channel: str, method: str,
) -> dict[str, Any]:
    published_at = published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if published else ""
    return {
        "id": item_id(source["id"], url, title),
        "sourceId": source["id"],
        "source": source["name"],
        "title": clean_text(title, 280),
        "url": canonical_url(url),
        "publishedAt": published_at,
        "datePrecision": "published" if published else "discovered",
        "excerpt": clean_text(excerpt, 460),
        "channel": channel,
        "method": method,
        "category": source["category"],
        "tier": source["tier"],
        "access": source["access"],
        "author": source["author"],
    }


def enrich_page_item(item: dict[str, Any]) -> dict[str, Any]:
    try:
        raw, final_url, _ = fetch(item["url"])
        parser = MetadataParser()
        parser.feed(raw.decode("utf-8", errors="replace"))
        meta = parser.meta
        title = meta.get("og:title") or meta.get("twitter:title") or clean_text(" ".join(parser.title_parts), 280)
        description = meta.get("og:description") or meta.get("twitter:description") or meta.get("description") or ""
        published = parse_datetime(
            meta.get("article:published_time") or meta.get("datepublished") or meta.get("date") or meta.get("pubdate")
        )
        if title and len(title) >= 8:
            item["title"] = clean_text(title, 280)
        if description:
            item["excerpt"] = clean_text(description, 460)
        if published:
            item["publishedAt"] = published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            item["datePrecision"] = "published"
        item["url"] = canonical_url(final_url)
        item["id"] = item_id(item["sourceId"], item["url"], item["title"])
    except Exception:
        pass
    return item


def parse_page(raw: bytes, source: dict[str, Any], final_url: str) -> list[dict[str, Any]]:
    parser = LinkParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    parser.close()
    include = re.compile(source.get("include_pattern", "."), re.I)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for link in parser.links:
        title = link["title"].strip(" -|•·")
        url = canonical_url(link["href"], final_url)
        if not url or url in seen or not include.search(url):
            continue
        if len(title) < 8 or title.lower() in SKIP_TITLES or title.lower().startswith(("view ", "read more", "see ")):
            continue
        seen.add(url)
        output.append(make_item(source, title, url, context_date(link["context"]), "", "网页索引", "page"))
        if len(output) >= 24:
            break
    detail_limit = min(10, len(output))
    for index in range(detail_limit):
        output[index] = enrich_page_item(output[index])
    return output


def collect_source(source: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    successes: list[str] = []
    for feed in source.get("feeds", []):
        try:
            raw, final_url, _ = fetch(feed["url"])
            parsed = parse_youtube_page(raw, source, feed) if feed.get("type") == "youtube_page" else parse_feed(raw, source, feed, final_url)
            items.extend(parsed)
            successes.append(f"{feed.get('channel', 'RSS')} {len(parsed)}条")
        except Exception as exc:
            errors.append(f"{feed.get('channel', 'RSS')}：{type(exc).__name__} {str(exc)[:90]}")
    if source.get("page") and (not source.get("feeds") or not items):
        try:
            raw, final_url, _ = fetch(source["page"])
            parsed = parse_page(raw, source, final_url)
            items.extend(parsed)
            successes.append(f"网页索引 {len(parsed)}条")
        except Exception as exc:
            errors.append(f"网页索引：{type(exc).__name__} {str(exc)[:90]}")
    unique = {item["id"]: item for item in items}
    items = list(unique.values())
    items.sort(key=lambda item: item.get("publishedAt") or "", reverse=True)
    if successes and errors:
        status = "部分可用"
    elif successes:
        status = "正常"
    else:
        status = "抓取失败"
    return {
        "source": source,
        "items": items,
        "status": status,
        "method": "；".join(successes) if successes else "无可用结果",
        "error": "；".join(errors),
    }


def discover_tags(item: dict[str, Any]) -> list[str]:
    haystack = f" {item['title']} {item.get('excerpt', '')} ".lower()
    tags = [label for label, words in TAGS.items() if any(word in haystack for word in words)]
    return tags[:6]


def discover_tickers(item: dict[str, Any]) -> list[str]:
    haystack = f" {item['title']} {item.get('excerpt', '')} ".lower()
    return [ticker for ticker, words in TICKERS.items() if any(word in haystack for word in words)][:6]


def effective_date(item: dict[str, Any]) -> date:
    parsed = parse_datetime(item.get("publishedAt"))
    if parsed:
        return parsed.date()
    return date.fromisoformat(item["firstSeen"])


def iso_week_key(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def week_label(key: str) -> str:
    match = re.fullmatch(r"(\d{4})-W(\d{2})", key)
    if not match:
        return key
    monday = date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
    return f"{monday.isoformat()} — {(monday + timedelta(days=6)).isoformat()}"


def score_item(item: dict[str, Any], today: date) -> int:
    tier_bonus = {0: 8, 1: 30, 2: 23, 3: 21, 4: 22, 5: 24, 6: 21, 7: 19}.get(item["tier"], 10)
    age = max(0, (today - effective_date(item)).days)
    recency = max(0, 30 - min(age, 30))
    tag_score = min(22, len(item.get("tags", [])) * 4)
    text = f"{item['title']} {item.get('excerpt', '')}".lower()
    depth = 10 if re.search(r"\b(report|analysis|outlook|state of|deep dive|history|economics|architecture|roadmap|primer)\b", text) else 3
    evidence = 5 if item.get("excerpt") else 0
    precision = 0 if item.get("datePrecision") == "published" else -10
    return max(1, min(100, tier_bonus + recency + tag_score + depth + evidence + precision))


def featured_ids(items: list[dict[str, Any]], week: str, limit: int = 16) -> list[str]:
    candidates = sorted((item for item in items if item["week"] == week), key=lambda item: (-item["score"], item["source"], item["title"]))
    selected: list[str] = []
    source_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    for item in candidates:
        if source_counts[item["sourceId"]] >= 2 or category_counts[item["category"]] >= 4:
            continue
        selected.append(item["id"])
        source_counts[item["sourceId"]] += 1
        category_counts[item["category"]] += 1
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for item in candidates:
            if item["id"] not in selected:
                selected.append(item["id"])
            if len(selected) >= limit:
                break
    return selected


def main() -> int:
    config = load_json(CONFIG_PATH, {})
    sources = config.get("sources", [])
    if not sources:
        raise SystemExit("weekly_news_sources.json has no sources")
    try:
        tz = ZoneInfo(config.get("timezone", "Asia/Singapore"))
    except ZoneInfoNotFoundError:
        # Minimal Windows Python installs may not ship the IANA database.
        # Singapore has no daylight-saving transitions, so UTC+8 is exact.
        tz = timezone(timedelta(hours=8), name="Asia/Singapore")
    now = datetime.now(tz)
    today = now.date()
    report_day = today - timedelta(days=7) if today.weekday() == 0 else today
    latest_week = iso_week_key(report_day)
    previous = load_json(HISTORY_PATH, {"version": 1, "items": [], "runs": []})
    previous_by_id = {item["id"]: item for item in previous.get("items", [])}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(collect_source, sources))

    collected: dict[str, dict[str, Any]] = {}
    for result in results:
        for item in result["items"]:
            old = previous_by_id.get(item["id"], {})
            item["firstSeen"] = old.get("firstSeen", today.isoformat())
            if not item.get("publishedAt") and old.get("publishedAt"):
                item["publishedAt"] = old["publishedAt"]
                item["datePrecision"] = old.get("datePrecision", "published")
            if not item.get("excerpt") and old.get("excerpt"):
                item["excerpt"] = old["excerpt"]
            collected[item["id"]] = item

    cutoff = today - timedelta(days=int(config.get("retention_days", 400)))
    for old_id, old in previous_by_id.items():
        try:
            keep = effective_date(old) >= cutoff
        except (KeyError, ValueError):
            keep = False
        if keep and old_id not in collected:
            collected[old_id] = old

    items = list(collected.values())
    for item in items:
        item["tags"] = discover_tags(item)
        item["tickers"] = discover_tickers(item)
        item["lens"] = CATEGORY_LENS[item["category"]]
        item["week"] = iso_week_key(effective_date(item))
        item["score"] = score_item(item, today)
        item["isNew"] = item["firstSeen"] == today.isoformat()
    items.sort(key=lambda item: (effective_date(item), item["score"], item["source"], item["title"]), reverse=True)

    source_rows: list[dict[str, Any]] = []
    for result in results:
        source = result["source"]
        source_items = [item for item in items if item["sourceId"] == source["id"]]
        dated = [effective_date(item) for item in source_items]
        source_rows.append({
            "id": source["id"], "name": source["name"], "tier": source["tier"],
            "category": source["category"], "author": source["author"], "focus": source["focus"],
            "access": source["access"], "homepage": source["homepage"], "status": result["status"],
            "method": result["method"], "error": result["error"],
            "latestItemDate": max(dated).isoformat() if dated else "", "storedItems": len(source_items),
            "latestWeekItems": sum(item["week"] == latest_week for item in source_items),
        })

    week_counts: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        week_counts.setdefault(item["week"], []).append(item)
    weeks = []
    for key, rows in sorted(week_counts.items(), reverse=True):
        theme_counts = Counter(tag for item in rows for tag in item.get("tags", []))
        weeks.append({
            "key": key, "label": week_label(key), "items": len(rows),
            "sources": len({item["sourceId"] for item in rows}),
            "new": sum(bool(item.get("isNew")) for item in rows),
            "themes": [name for name, _ in theme_counts.most_common(5)],
        })
    if latest_week not in week_counts and weeks:
        latest_week = weeks[0]["key"]

    new_ids = [item["id"] for item in items if item.get("isNew")]
    run = {
        "week": latest_week,
        "generatedAt": now.isoformat(timespec="seconds"),
        "newItemIds": new_ids,
        "sourceFailures": [row["id"] for row in source_rows if row["status"] == "抓取失败"],
    }
    runs = previous.get("runs", [])
    existing_run = next((entry for entry in runs if entry.get("week") == latest_week), None)
    if existing_run:
        run["newItemIds"] = sorted(set(existing_run.get("newItemIds", [])) | set(new_ids))
        existing_run.update(run)
    else:
        runs.append(run)
    runs = sorted(runs, key=lambda entry: entry.get("week", ""), reverse=True)[:104]

    generated_at = now.isoformat(timespec="seconds")
    output = {
        "version": 1,
        "generatedAt": generated_at,
        "schedule": config.get("schedule_description", "每周"),
        "timezone": config.get("timezone", "Asia/Singapore"),
        "latestWeek": latest_week,
        "latestWeekLabel": week_label(latest_week),
        "categories": config.get("categories", {}),
        "stats": {
            "sources": len(source_rows),
            "activeSources": sum(row["status"] != "抓取失败" for row in source_rows),
            "failedSources": sum(row["status"] == "抓取失败" for row in source_rows),
            "storedItems": len(items),
            "latestWeekItems": sum(item["week"] == latest_week for item in items),
            "latestWeekSources": len({item["sourceId"] for item in items if item["week"] == latest_week}),
        },
        "featuredIds": featured_ids(items, latest_week),
        "weeks": weeks,
        "sources": source_rows,
        "items": items,
        "methodology": {
            "scope": "仅保存公开标题、链接和不超过460字的公开摘要；不绕过登录或付费墙。",
            "ranking": "优先级综合来源梯队、时效、主题命中、内容深度线索和公开摘要完整度；它是阅读排序，不是投资评分。",
            "dates": "有发布日期时按发布日期归周；网页索引无法核对日期时按首次发现日归周并明确标记。",
            "deduplication": "同一来源按规范化链接去重；跨来源的同一主题保留，以便观察信息扩散。",
        },
    }
    state = {"version": 1, "generatedAt": generated_at, "items": items, "runs": runs}
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"OK: {len(source_rows)} sources, {len(items)} stored items, {output['stats']['latestWeekItems']} in {latest_week}")
    print(f"    active={output['stats']['activeSources']} failed={output['stats']['failedSources']} -> {OUTPUT_PATH}")
    for row in source_rows:
        if row["status"] != "正常":
            print(f"  {row['status']}: {row['name']} — {row['error'] or row['method']}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
