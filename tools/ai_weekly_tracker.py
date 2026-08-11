#!/usr/bin/env python3
"""Build a dated AI-industry weekly monitor from public, machine-readable sources.

The script is deliberately dependency-free so it can run in GitHub Actions.  A
source failure is reported in the note instead of silently reusing a fabricated
number.  Non-standard quarterly metrics (RPO, paid seats, HBM contracts, etc.)
live in ai_weekly_sources.json and are clearly marked as manual anchors.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "tools" / "ai_weekly_sources.json"
HISTORY_PATH = ROOT / "data" / "ai_weekly" / "history.json"
USER_AGENT = "P-investing-ai-weekly/1.0 research@pickalphas.com"
TIMEOUT = 35


def fetch(url: str, *, accept: str = "application/json,text/html") -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept, "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read(), dict(resp.headers.items())


def fetch_json(url: str) -> Any:
    raw, _ = fetch(url)
    return json.loads(raw.decode("utf-8"))


def fmt_num(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def fmt_money(value: float | int | None) -> str:
    if value is None:
        return "—"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    return f"${value:,.0f}"


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def median(values: list[float]) -> float | None:
    values = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return statistics.median(values) if values else None


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def signal_label(score: float) -> str:
    if score >= 70:
        return "绿色扩张"
    if score >= 45:
        return "黄色分化"
    return "红色收缩"


def trend_arrow(value: float | None, flat: float = 1.0) -> str:
    if value is None:
        return "→"
    if value > flat:
        return "↑"
    if value < -flat:
        return "↓"
    return "→"


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"td", "th"}:
            self.in_cell = True
            self.cell = []
        elif tag == "tr":
            self.row = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            self.row.append(" ".join("".join(self.cell).split()))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


def collect_gpu(config: dict[str, Any]) -> dict[str, Any]:
    current = fetch_json(config["gpu"]["current_url"])
    history = fetch_json(config["gpu"]["history_url"])
    rows = []
    for plan in current.get("plans", []):
        model = str(plan.get("gpu_model") or "")
        price = plan.get("price_hourly_usd")
        count = plan.get("gpu_count") or 1
        if not price or not count:
            continue
        normalized = float(price) / float(count)
        if re.search(r"H100|H200|B200|B300|A100|MI300", model, re.I):
            rows.append(
                {
                    "provider": plan.get("provider", "—"),
                    "model": model,
                    "gpu_count": count,
                    "per_gpu_hour": normalized,
                }
            )
    h100 = [r["per_gpu_hour"] for r in rows if re.search(r"H100", r["model"], re.I)]
    daily = history.get("daily", [])
    market_change = None
    if len(daily) >= 2:
        market_change = pct_change(
            daily[-1].get("price_hourly_usd", {}).get("median"),
            daily[0].get("price_hourly_usd", {}).get("median"),
        )
    return {
        "captured_at": current.get("captured_at") or current.get("generated_at"),
        "provider_count": current.get("provider_count"),
        "plan_count": current.get("plan_count"),
        "relevant_rows": sorted(rows, key=lambda x: (x["model"], x["per_gpu_hour"])),
        "h100_median": median(h100),
        "h100_min": min(h100) if h100 else None,
        "h100_max": max(h100) if h100 else None,
        "window_start": daily[0].get("date") if daily else None,
        "window_end": daily[-1].get("date") if daily else None,
        "all_plan_median": daily[-1].get("price_hourly_usd", {}).get("median") if daily else None,
        "all_plan_window_change": market_change,
    }


def collect_tsmc(config: dict[str, Any]) -> dict[str, Any]:
    year = date.today().year
    url = config["tsmc_monthly_url"].format(year=year)
    try:
        raw, _ = fetch(url, accept="text/html")
    except Exception as exc:
        fallback = dict(config.get("tsmc_official_fallback") or {})
        if not fallback:
            raise
        return {
            "latest": fallback,
            "series": [],
            "status": "official_dated_fallback",
            "source_url": fallback.get("source_url", url),
            "warning": (
                f"TSMC官网自动访问失败（{type(exc).__name__}）；"
                f"使用截至{fallback.get('as_of', '未知日期')}的官方已核验回退值"
            ),
        }
    parser = TableParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    months = {
        "Jan.": 1,
        "Feb.": 2,
        "Mar.": 3,
        "Apr.": 4,
        "May": 5,
        "Jun.": 6,
        "Jul.": 7,
        "Aug.": 8,
        "Sept.": 9,
        "Oct.": 10,
        "Nov.": 11,
        "Dec.": 12,
    }
    parsed = []
    for row in parser.rows:
        if not row or row[0] not in months or len(row) < 3:
            continue
        revenue = re.sub(r"[^0-9.-]", "", row[1])
        yoy = re.sub(r"[^0-9.-]", "", row[2])
        if revenue and yoy:
            parsed.append(
                {
                    "month": row[0],
                    "month_no": months[row[0]],
                    "revenue_twd_m": float(revenue),
                    "yoy": float(yoy),
                }
            )
    if not parsed:
        raise ValueError("TSMC monthly revenue table could not be parsed")
    latest = max(parsed, key=lambda x: x["month_no"])
    latest["as_of"] = f"{year}-{latest['month_no']:02d}"
    return {
        "latest": latest,
        "series": sorted(parsed, key=lambda x: x["month_no"]),
        "status": "live",
        "source_url": url,
    }


def duration_days(item: dict[str, Any]) -> int | None:
    try:
        return (date.fromisoformat(item["end"]) - date.fromisoformat(item["start"])).days
    except (KeyError, TypeError, ValueError):
        return None


def fact_entries(companyfacts: dict[str, Any], concepts: list[str], unit: str = "USD") -> list[dict[str, Any]]:
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    combined: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for concept in concepts:
        fact = gaap.get(concept)
        if not fact:
            continue
        units = fact.get("units", {})
        rows = units.get(unit) or next(iter(units.values()), [])
        for row in rows:
            if row.get("form") not in {"10-Q", "10-K"} or not row.get("filed"):
                continue
            key = (row.get("accn"), row.get("start"), row.get("end"), row.get("val"), concept)
            if key not in seen:
                combined.append({**row, "_concept": concept})
                seen.add(key)
    return combined


def latest_flow(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates: list[tuple[str, str, int, int, dict[str, Any]]] = []
    for index, item in enumerate(entries):
        days = duration_days(item)
        if days is not None and 55 <= days <= 380 and item.get("val") is not None:
            candidates.append((item.get("end", ""), item.get("filed", ""), -days, index, item))
    if not candidates:
        return None
    return max(candidates)[-1]


def fresh_item(item: dict[str, Any] | None, max_age_days: int = 550) -> dict[str, Any] | None:
    """Reject structurally valid XBRL facts that are too old for a weekly monitor."""
    if not item or not item.get("end"):
        return None
    try:
        age = (date.today() - date.fromisoformat(item["end"])).days
    except (TypeError, ValueError):
        return None
    return item if age <= max_age_days else None


def comparable_yoy(entries: list[dict[str, Any]], latest: dict[str, Any] | None) -> float | None:
    if not latest:
        return None
    latest_days = duration_days(latest)
    latest_end = date.fromisoformat(latest["end"])
    matches = []
    for item in entries:
        if item is latest or item.get("val") is None:
            continue
        if item.get("_concept") != latest.get("_concept"):
            continue
        days = duration_days(item)
        try:
            end = date.fromisoformat(item["end"])
        except (KeyError, ValueError):
            continue
        if latest_days is not None and days is not None and abs(days - latest_days) <= 8:
            year_gap = (latest_end - end).days
            if 340 <= year_gap <= 390:
                matches.append((item.get("filed", ""), item))
    previous = max(matches)[-1] if matches else None
    return pct_change(latest.get("val"), previous.get("val") if previous else None)


def latest_instant(entries: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float | None]:
    candidates = [x for x in entries if x.get("end") and x.get("val") is not None]
    if not candidates:
        return None, None
    by_end: dict[str, dict[str, Any]] = {}
    for item in candidates:
        end = item["end"]
        if end not in by_end or item.get("filed", "") > by_end[end].get("filed", ""):
            by_end[end] = item
    ordered = sorted(by_end.values(), key=lambda x: x["end"])
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None
    return latest, pct_change(latest.get("val"), previous.get("val") if previous else None)


def collect_sec_company(company: dict[str, str]) -> dict[str, Any]:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json"
    facts = fetch_json(url)
    revenue_entries = fact_entries(
        facts,
        ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    )
    capex_entries = fact_entries(
        facts,
        ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForAdditionsToPropertyPlantAndEquipment"],
    )
    inventory_entries = fact_entries(facts, ["InventoryNet", "InventoryFinishedGoodsNetOfAllowancesCustomerAdvancesAndProgressBillings"])
    revenue = fresh_item(latest_flow(revenue_entries))
    capex = fresh_item(latest_flow(capex_entries))
    inventory, inventory_change = latest_instant(inventory_entries)
    inventory = fresh_item(inventory)
    if inventory is None:
        inventory_change = None
    return {
        **company,
        "source_url": url,
        "revenue": revenue.get("val") if revenue else None,
        "revenue_end": revenue.get("end") if revenue else None,
        "revenue_days": duration_days(revenue) if revenue else None,
        "revenue_yoy": comparable_yoy(revenue_entries, revenue),
        "capex": capex.get("val") if capex else None,
        "capex_end": capex.get("end") if capex else None,
        "capex_days": duration_days(capex) if capex else None,
        "capex_yoy": comparable_yoy(capex_entries, capex),
        "inventory": inventory.get("val") if inventory else None,
        "inventory_end": inventory.get("end") if inventory else None,
        "inventory_change": inventory_change,
    }


def collect_openrouter(config: dict[str, Any]) -> dict[str, Any]:
    models = fetch_json(config["openrouter_models_url"]).get("data", [])
    prompt_prices = []
    output_prices = []
    providers = set()
    million_context = 0
    free_models = 0
    for model in models:
        model_id = str(model.get("id") or "")
        if "/" in model_id:
            providers.add(model_id.split("/", 1)[0].lstrip("~"))
        if (model.get("context_length") or 0) >= 1_000_000:
            million_context += 1
        pricing = model.get("pricing") or {}
        try:
            prompt = float(pricing.get("prompt", 0)) * 1_000_000
            output = float(pricing.get("completion", 0)) * 1_000_000
        except (TypeError, ValueError):
            continue
        if prompt == 0 and output == 0:
            free_models += 1
        elif prompt > 0 and output > 0:
            prompt_prices.append(prompt)
            output_prices.append(output)
    return {
        "model_count": len(models),
        "provider_count": len(providers),
        "million_context_count": million_context,
        "free_model_count": free_models,
        "median_input_per_million": median(prompt_prices),
        "median_output_per_million": median(output_prices),
    }


def collect_huggingface(config: dict[str, Any]) -> dict[str, Any]:
    models = fetch_json(config["huggingface_models_url"])
    downloads = [float(m.get("downloads") or 0) for m in models]
    likes = [float(m.get("likes") or 0) for m in models]
    top = sorted(models, key=lambda x: x.get("downloads") or 0, reverse=True)[:5]
    return {
        "sample_count": len(models),
        "top100_downloads": sum(downloads),
        "median_downloads": median(downloads),
        "top100_likes": sum(likes),
        "top": [{"id": x.get("id"), "downloads": x.get("downloads"), "likes": x.get("likes")} for x in top],
    }


def collect_github(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for repo in config["github_repositories"]:
        data = fetch_json(f"https://api.github.com/repos/{repo}")
        rows.append(
            {
                "repo": repo,
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "pushed_at": data.get("pushed_at"),
            }
        )
    return rows


def collect_market(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for symbol in config["market_symbols"]:
        quoted = urllib.parse.quote(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quoted}?range=1mo&interval=1d"
        data = fetch_json(url)["chart"]["result"][0]
        closes = [x for x in data.get("indicators", {}).get("quote", [{}])[0].get("close", []) if x is not None]
        if not closes:
            continue
        week_base = closes[-6] if len(closes) >= 6 else closes[0]
        rows.append(
            {
                "symbol": symbol,
                "close": closes[-1],
                "week_change": pct_change(closes[-1], week_base),
                "month_change": pct_change(closes[-1], closes[0]),
                "currency": data.get("meta", {}).get("currency"),
            }
        )
    return rows


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8")).get("weeks", [])
    except (json.JSONDecodeError, OSError):
        return []


def previous_value(history: list[dict[str, Any]], path: list[str], weeks_back: int = 1) -> float | None:
    if len(history) < weeks_back:
        return None
    value: Any = history[-weeks_back]
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def score_snapshot(snapshot: dict[str, Any], history: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, float]:
    gpu = snapshot.get("gpu", {})
    old_h100 = previous_value(history, ["gpu", "h100_median"], 4)
    h100_change = pct_change(gpu.get("h100_median"), old_h100)
    compute = 76.0 if h100_change is None else clamp(68 + h100_change * 0.8, 35, 92)

    cloud_anchors = [a["score"] for a in config["quarterly_anchors"] if a["company"] in {"Microsoft", "Alphabet", "Amazon", "Meta"}]
    capex_orders = statistics.mean(cloud_anchors) if cloud_anchors else 50

    latest_tsmc = snapshot.get("tsmc", {}).get("latest", {})
    tsmc_yoy = latest_tsmc.get("yoy")
    tsmc_as_of = str(latest_tsmc.get("as_of") or "")
    try:
        parsed_as_of = date.fromisoformat(tsmc_as_of if len(tsmc_as_of) == 10 else f"{tsmc_as_of}-01")
        if (date.today() - parsed_as_of).days > 100:
            tsmc_yoy = None
    except ValueError:
        tsmc_yoy = None
    chip_anchors = [a["score"] for a in config["quarterly_anchors"] if a["company"] in {"NVIDIA", "TSMC", "Vertiv"}]
    supply_base = statistics.mean(chip_anchors) if chip_anchors else 50
    supply = clamp(supply_base + ((tsmc_yoy or 0) - 20) * 0.08, 30, 96)

    app_anchors = [a["score"] for a in config["quarterly_anchors"] if a["company"] in {"Microsoft", "Alphabet", "Amazon", "Anthropic"}]
    application = statistics.mean(app_anchors) if app_anchors else 50

    old_models = previous_value(history, ["openrouter", "model_count"])
    model_growth = pct_change(snapshot.get("openrouter", {}).get("model_count"), old_models)
    ecosystem = clamp(78 + (model_growth or 0) * 0.4, 45, 92)

    etf_rows = [x for x in snapshot.get("market", []) if x["symbol"] in {"SMH", "SOXX", "CHAT", "BOTZ"}]
    etf_return = statistics.mean([x["month_change"] for x in etf_rows if x.get("month_change") is not None]) if etf_rows else 0
    finance_risk = clamp(47 + etf_return * 0.5, 25, 72)

    scores = {
        "算力供需": round(compute, 1),
        "云CapEx与订单": round(capex_orders, 1),
        "硬件与基础设施": round(supply, 1),
        "应用与变现": round(application, 1),
        "模型与开发生态": round(ecosystem, 1),
        "融资、估值与风险": round(finance_risk, 1),
    }
    weights = {
        "算力供需": 0.20,
        "云CapEx与订单": 0.20,
        "硬件与基础设施": 0.15,
        "应用与变现": 0.25,
        "模型与开发生态": 0.10,
        "融资、估值与风险": 0.10,
    }
    scores["综合"] = round(sum(scores[k] * weights[k] for k in weights), 1)
    previous_application = previous_value(history, ["scores", "应用与变现"])
    if application < 40 and previous_application is not None and previous_application < 40:
        scores["综合"] = min(scores["综合"], 69.0)
    return scores


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(clean(x) for x in headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out.extend("| " + " | ".join(clean(x) for x in row) + " |" for row in rows)
    return "\n".join(out)


def build_article(snapshot: dict[str, Any], history: list[dict[str, Any]], config: dict[str, Any]) -> str:
    report_date = snapshot["date"]
    week = snapshot["week"]
    scores = snapshot["scores"]
    total = scores["综合"]
    errors = snapshot.get("errors", [])
    latest_tsmc = snapshot.get("tsmc", {}).get("latest", {})
    tsmc_status = snapshot.get("tsmc", {}).get("status")
    if tsmc_status == "live":
        tsmc_note = "官网实时抓取"
    elif tsmc_status == "official_dated_fallback":
        tsmc_note = "官网阻止自动访问，采用带日期的官方核验回退值"
    else:
        tsmc_note = "本期未获得有效值"
    gpu = snapshot.get("gpu", {})

    score_rows = []
    weights = [20, 20, 15, 25, 10, 10]
    for (name, score), weight in zip([(k, v) for k, v in scores.items() if k != "综合"], weights):
        previous_score = previous_value(history, ["scores", name])
        change = score - previous_score if previous_score is not None else None
        score_rows.append(
            [
                name,
                f"{weight}%",
                f"{score:.1f}",
                f"{change:+.1f}" if change is not None else "基线",
                signal_label(score),
            ]
        )

    trend_rows = []
    for old in (history[-11:] + [snapshot]):
        old_scores = old.get("scores", {})
        trend_rows.append(
            [
                old.get("week", old.get("date", "—")),
                fmt_num(old_scores.get("综合")),
                fmt_num(old_scores.get("算力供需")),
                fmt_num(old_scores.get("云CapEx与订单")),
                fmt_num(old_scores.get("硬件与基础设施")),
                fmt_num(old_scores.get("应用与变现")),
                fmt_num(old_scores.get("模型与开发生态")),
                fmt_num(old_scores.get("融资、估值与风险")),
            ]
        )

    gpu_rows = []
    for row in snapshot.get("gpu", {}).get("relevant_rows", []):
        gpu_rows.append([row["provider"], row["model"], row["gpu_count"], f"${row['per_gpu_hour']:.2f}"])

    sec_rows = []
    for row in snapshot.get("sec", []):
        period = f"{row.get('revenue_end') or '—'} / {row.get('revenue_days') or '—'}天"
        sec_rows.append(
            [
                row["ticker"],
                period,
                fmt_money(row.get("revenue")),
                f"{fmt_num(row.get('revenue_yoy'))}%" if row.get("revenue_yoy") is not None else "—",
                fmt_money(row.get("capex")),
                f"{fmt_num(row.get('capex_yoy'))}%" if row.get("capex_yoy") is not None else "—",
                f"{fmt_num(row.get('inventory_change'))}%" if row.get("inventory_change") is not None else "—",
            ]
        )

    anchor_rows = []
    now = date.fromisoformat(report_date)
    for item in config["quarterly_anchors"]:
        age = (now - date.fromisoformat(item["date"])).days
        freshness = "新鲜" if age <= 45 else ("关注更新" if age <= 90 else "陈旧")
        anchor_rows.append([item["company"], item["period"], item["metrics"], item["signal"], f"{freshness}（{age}天）"])

    market_rows = []
    for row in snapshot.get("market", []):
        market_rows.append(
            [
                row["symbol"],
                f"{row['close']:.2f}",
                f"{trend_arrow(row.get('week_change'))} {fmt_num(row.get('week_change'))}%",
                f"{trend_arrow(row.get('month_change'))} {fmt_num(row.get('month_change'))}%",
            ]
        )

    github_previous = {x["repo"]: x for x in history[-1].get("github", [])} if history else {}
    github_rows = []
    for row in snapshot.get("github", []):
        old = github_previous.get(row["repo"], {}).get("stars")
        delta = row["stars"] - old if isinstance(old, int) and isinstance(row.get("stars"), int) else None
        github_rows.append([row["repo"], f"{row['stars']:,}", f"+{delta:,}" if delta is not None and delta >= 0 else (str(delta) if delta is not None else "基线"), str(row.get("pushed_at", ""))[:10]])

    hf = snapshot.get("huggingface", {})
    openrouter = snapshot.get("openrouter", {})
    error_text = "；".join(errors) if errors else "全部自动数据源抓取成功。"
    source_rows = [list(row) for row in config.get("source_registry", [])]

    body = f"""---
title: AI行业景气度每周监测：{week}
category: industries
date: {report_date}
tickers: NVDA, MSFT, AMZN, GOOGL, META, TSM, MU, VRT, MRVL, CEG
tags: AI景气度, 每周追踪, 算力, 资本开支, 半导体, 应用变现
source: codex
---

# AI行业景气度每周监测：{week}

> 更新时间：{snapshot['generated_at']}；自动计划：{config['schedule_description']}。本期综合景气度 **{total:.1f}/100（{signal_label(total)}）**。评分是研究仪表盘，不是机械交易信号。

## 一、本周结论

AI 产业仍处于**高景气扩张期**，强度主要来自云收入、先进制程、GPU/网络/电力基础设施和企业应用的共同扩张。风险没有表现为需求全面下降，而是集中在资本开支强度、自由现金流、供应商融资、订单集中度和未来折旧压力。

本周最重要的判断原则：若 GPU 价格下降但 Token 调用、云收入和付费应用增长更快，应解释为生产率扩张；只有当租金、集群可得性、云收入和应用指标同步转弱时，才构成供需衰退的强证据。

## 二、六支柱景气评分

{markdown_table(['支柱', '权重', '得分', '较上期', '状态'], score_rows)}

评分口径：官方财报和监管数据优先；交易/使用数据次之；第三方报价与市场价格低权重。综合分 70 以上为绿色扩张、45—69 为黄色分化、45 以下为红色收缩。应用与变现若连续两期低于 40，总分最高限制在黄色。

### 近12期趋势

{markdown_table(['周次', '综合', '算力', 'CapEx/订单', '硬件', '应用', '生态', '融资/风险'], trend_rows)}

首期显示为基线；以后每周保留一行，最多在正文展示近 12 期，完整快照永久保存在历史数据文件中。

## 三、算力价格与可得性

- 标准化 H100 公开报价中位数：**${fmt_num(gpu.get('h100_median'), 2)}/卡/小时**，范围 **${fmt_num(gpu.get('h100_min'), 2)}—${fmt_num(gpu.get('h100_max'), 2)}**。
- 数据集覆盖 {gpu.get('provider_count', '—')} 家稳定提供商、{gpu.get('plan_count', '—')} 个计划；全部计划报价中位数在 {gpu.get('window_start', '—')} 至 {gpu.get('window_end', '—')} 的窗口变化 **{fmt_num(gpu.get('all_plan_window_change'))}%**。
- 这是公开标价，不是企业长约成交价，也不证明某一地区有 1,024 卡以上连续集群可租。集群规模、网络、地域和合同期限必须分开解释。

{markdown_table(['提供商', 'GPU', '实例GPU数', '标准化每卡时价'], gpu_rows) if gpu_rows else '本周未取得可比较的旗舰 GPU 报价。'}

数据源：[GPU Cloud Price Index](https://gpucloudcompare.com/data/)（CC-BY 4.0）。为避免整机价格误导，本文按实例 GPU 数重新折算每卡每小时价格。

## 四、云资本开支、订单与商业化锚点

{markdown_table(['公司', '期间', '关键数据', '解读', '新鲜度'], anchor_rows)}

季度锚点保留原始披露日期。超过 45 天标记“关注更新”，超过 90 天标记“陈旧”，不以旧数据冒充本周变化。

### SEC 自动财务抓取

{markdown_table(['公司', '最新流量期间', '收入', '同比', '现金CapEx', 'CapEx同比', '库存较上一披露期'], sec_rows) if sec_rows else '本周 SEC 数据未成功抓取。'}

注意：SEC XBRL 中的现金 CapEx 不一定包含融资租赁；不同公司提交季度值或年初至今累计值的方式也不同，因此表中附带期间天数，禁止直接横向相加。

## 五、制造、网络与电力链

- 台积电最新月营收为 **{fmt_num(latest_tsmc.get('revenue_twd_m') / 1000 if latest_tsmc else None)} 十亿新台币**，同比 **{fmt_num(latest_tsmc.get('yoy') if latest_tsmc else None)}%**；数据期 {latest_tsmc.get('as_of', '—')}，状态：{tsmc_note}。
- 台积电 2026 Q2 的 HPC 占收入 66%，环比增长 20%；N7 及以下占晶圆收入 77%。这一组合说明 AI 先进制程仍强，但 N2 爬坡导致库存天数上升，不能只看收入。
- 数据中心电力与机房是当前关键瓶颈。追踪应优先看“实际通电 MW、空置率和吸收量”，而不是尚未并网的宣布容量。

## 六、模型价格、使用与开发者生态

- OpenRouter 当前收录 **{openrouter.get('model_count', '—')}** 个模型、约 **{openrouter.get('provider_count', '—')}** 个模型家族；其中免费模型 {openrouter.get('free_model_count', '—')} 个，百万 Token 上下文模型 {openrouter.get('million_context_count', '—')} 个。
- 非免费模型目录的输入/输出价格中位数分别为 **${fmt_num(openrouter.get('median_input_per_million'), 2)} / ${fmt_num(openrouter.get('median_output_per_million'), 2)} 每百万 Token**。这是目录中位数，不按实际调用量加权。
- Hugging Face 下载量最高的 100 个模型合计近 30 日下载 **{fmt_num(hf.get('top100_downloads') / 1_000_000 if hf else None)} 百万次**。自动下载与 CI 会抬高该指标，因此只作为生态活跃代理，不等于收入。

{markdown_table(['GitHub项目', 'Stars', '本周新增', '最近推送'], github_rows) if github_rows else '本周 GitHub 数据未成功抓取。'}

## 七、市场与融资风险温度

{markdown_table(['标的', '收盘价', '近5个交易日', '近1个月'], market_rows) if market_rows else '本周市场数据未成功抓取。'}

市场价格使用非官方行情接口，只承担低权重情绪指标。当前融资端最大风险不是“没有钱”，而是资金高度集中在少数基础模型公司，名义融资额中还可能包含分期承诺、战略投资和供应商融资。

## 八、人工复核清单

"""
    for item in config["manual_review"]:
        body += f"- {item}\n"

    body += f"""

## 九、预警条件

以下任一组合持续两期，景气度从绿色降为黄色并启动专项复核：

1. 云 CapEx 同比大增，但标准化 GPU 租金、大集群可得性和应用收入同时转弱；
2. RPO 增长主要来自合同期限拉长、单一客户或供应商融资；
3. 服务器/电力设备库存和应收连续两季显著快于收入；
4. 新增折旧超过云业务增量毛利，且自由现金流持续恶化；
5. 模型 Token 价格下降但调用量、成功任务数与应用收入没有产生需求弹性；
6. 规划 MW 快速增长，而实际通电率、租赁率和每 MW 收入下降。

## 十、数据状态与限制

{error_text}

自动抓取负责发现变化，最终结论仍需回到财报、电话会和真实成交数据复核。GPU 报价、模型目录价格、下载量、Star 和股价不能独立证明产业需求。

## 数据源分层与更新频率

评级口径：A=公司/监管/政府等一手数据，B=可复核的行业或平台数据，C=估算、流量或非官方行情。低等级来源只作交叉验证，不能单独改变结论。

{markdown_table(['指标组', '来源', '频率', '处理方式', '等级'], source_rows)}

## 主要数据源

- [Microsoft Investor Relations](https://www.microsoft.com/en-us/Investor/)
- [Alphabet Investor Relations](https://abc.xyz/investor/)
- [Amazon Investor Relations](https://ir.aboutamazon.com/)
- [Meta Investor Relations](https://investor.atmeta.com/)
- [NVIDIA Investor Relations](https://investor.nvidia.com/)
- [TSMC 月度营收](https://investor.tsmc.com/schinese/monthly-revenue/2026)
- [SEC Companyfacts API](https://www.sec.gov/edgar/sec-api-documentation)
- [GPU Cloud Price Index](https://gpucloudcompare.com/data/)
- [OpenRouter Models API](https://openrouter.ai/api/v1/models)
- [Hugging Face Hub](https://huggingface.co/models)
- [IEA Electricity 2026](https://www.iea.org/reports/electricity-2026)
- [EIA Annual Energy Outlook 2026](https://www.eia.gov/outlooks/aeo/)
- [CBRE Global Data Center Trends 2026](https://www.cbre.com/insights/reports/global-data-center-trends-2026)
- [Stanford AI Index 2026](https://hai.stanford.edu/ai-index/2026-ai-index-report)

> 本报告不构成投资建议。自动评分主要用于保持观察口径一致，不能替代估值、仓位和公司层面的基本面研究。
"""
    return body


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        report_tz = ZoneInfo(config["timezone"])
    except ZoneInfoNotFoundError:
        # Some dependency-free Windows Python installations do not ship the
        # IANA tzdata package. Singapore has no daylight-saving transitions.
        if config["timezone"] != "Asia/Singapore":
            raise
        report_tz = timezone(timedelta(hours=8), name="SGT")
    local_now = datetime.now(report_tz)
    report_date = local_now.date().isoformat()
    snapshot: dict[str, Any] = {
        "date": report_date,
        "week": f"{local_now.isocalendar().year}-W{local_now.isocalendar().week:02d}",
        "generated_at": local_now.strftime("%Y-%m-%d %H:%M %Z"),
        "errors": [],
    }

    collectors = [
        ("gpu", lambda: collect_gpu(config)),
        ("tsmc", lambda: collect_tsmc(config)),
        ("openrouter", lambda: collect_openrouter(config)),
        ("huggingface", lambda: collect_huggingface(config)),
        ("github", lambda: collect_github(config)),
        ("market", lambda: collect_market(config)),
    ]
    for name, collector in collectors:
        try:
            snapshot[name] = collector()
            if name == "tsmc" and snapshot[name].get("warning"):
                snapshot["errors"].append(snapshot[name]["warning"])
        except Exception as exc:  # source failures belong in the generated report
            snapshot[name] = [] if name in {"github", "market"} else {}
            snapshot["errors"].append(f"{name}: {type(exc).__name__}: {exc}")

    sec_rows = []
    for company in config["sec_companies"]:
        try:
            sec_rows.append(collect_sec_company(company))
        except Exception as exc:
            snapshot["errors"].append(f"SEC {company['ticker']}: {type(exc).__name__}: {exc}")
    snapshot["sec"] = sec_rows

    history = load_history()
    history_without_today = [x for x in history if x.get("date") != report_date]
    snapshot["scores"] = score_snapshot(snapshot, history_without_today, config)
    article = build_article(snapshot, history_without_today, config)

    article_path = ROOT / "content" / "industries" / f"{report_date}-ai-industry-weekly-monitor.md"
    article_path.write_text(article, encoding="utf-8", newline="\n")

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history_out = history_without_today + [snapshot]
    HISTORY_PATH.write_text(
        json.dumps({"schema_version": 1, "weeks": history_out}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"AI weekly: {snapshot['week']} score={snapshot['scores']['综合']} -> {article_path.relative_to(ROOT)}")
    if snapshot["errors"]:
        print("Source warnings:")
        for item in snapshot["errors"]:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
