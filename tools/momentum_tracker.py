#!/usr/bin/env python3
"""Build the public-data momentum dashboard used by the static site.

The job is dependency-free so it can run on GitHub Actions.  It screens a
liquid large-cap US equity universe from Nasdaq, obtains adjusted price
history and reported fundamentals from Yahoo Finance's public JSON endpoints,
and writes a compact dashboard payload.  No PickAlphas credentials, sessions,
attachments, or proprietary report text are used.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import random
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "docs" / "momentum.json"
HISTORY_PATH = ROOT / "data" / "momentum" / "history.json"
NASDAQ_URL = (
    "https://api.nasdaq.com/api/screener/stocks"
    "?tableonly=true&limit=10000&offset=0&download=true"
)
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_FUNDAMENTALS = (
    "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 "
    "P-investing-momentum/1.0"
)
TIMEOUT = 45
DEFAULT_SYMBOLS = 180
DEFAULT_WORKERS = 10
BENCHMARK = "SPY"
PINNED = {
    "AAPL", "AMD", "AMZN", "ARM", "ASML", "AVGO", "BABA", "GOOG", "GOOGL",
    "META", "MSFT", "MU", "NBIS", "NFLX", "NVDA", "PLTR", "RKLB", "TSLA", "TSM",
}
FUNDAMENTAL_TYPES = [
    "annualTotalRevenue",
    "annualDilutedEPS",
    "annualNetIncome",
    "annualOperatingIncome",
    "annualFreeCashFlow",
    "annualStockholdersEquity",
    "annualTotalDebt",
    "annualCashCashEquivalentsAndShortTermInvestments",
    "annualInvestedCapital",
    "annualEBIT",
    "trailingTotalRevenue",
    "trailingNetIncome",
    "trailingOperatingIncome",
    "trailingFreeCashFlow",
    "trailingPeRatio",
    "trailingPsRatio",
    "trailingMarketCap",
]


def fetch_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Cache-Control": "no-cache",
    }
    request_headers.update(headers or {})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # network services occasionally throttle
            last_error = exc
            if attempt < 2:
                time.sleep((1.1**attempt) + random.random())
    assert last_error is not None
    raise last_error


def number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        cleaned = re.sub(r"[^0-9.eE+-]", "", str(value))
        if not cleaned:
            return None
        try:
            result = float(cleaned)
        except ValueError:
            return None
    return result if math.isfinite(result) else None


def rounded(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def pct(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def cagr(current: float | None, previous: float | None, years: int) -> float | None:
    if current is None or previous is None or current <= 0 or previous <= 0 or years <= 0:
        return None
    return ((current / previous) ** (1 / years) - 1) * 100


def mean(values: Iterable[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return statistics.fmean(clean) if clean else None


def change(closes: list[float], sessions: int) -> float | None:
    if len(closes) <= sessions:
        return None
    return pct(closes[-1], closes[-1 - sessions])


def yahoo_symbol(symbol: str) -> str:
    return symbol.replace(".", "-")


def load_universe(limit: int) -> list[dict[str, Any]]:
    payload = fetch_json(
        NASDAQ_URL,
        headers={
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com/market-activity/stocks/screener",
        },
    )
    rows = (((payload or {}).get("data") or {}).get("rows") or [])
    exclusions = re.compile(r"\b(etf|warrant|rights?|units?|closed[- ]end fund)\b", re.I)
    cleaned: list[dict[str, Any]] = []
    by_symbol: dict[str, dict[str, Any]] = {}
    for raw in rows:
        symbol = str(raw.get("symbol") or "").upper().strip()
        name = str(raw.get("name") or "").strip()
        market_cap = number(raw.get("marketCap"))
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,8}", symbol):
            continue
        if market_cap is None or market_cap < 500_000_000 or exclusions.search(name):
            continue
        item = {
            "symbol": symbol,
            "name": name,
            "sector": str(raw.get("sector") or "未分类").strip() or "未分类",
            "industry": str(raw.get("industry") or "未分类").strip() or "未分类",
            "marketCap": market_cap,
        }
        cleaned.append(item)
        by_symbol[symbol] = item
    cleaned.sort(key=lambda item: item["marketCap"], reverse=True)
    selected = cleaned[:limit]
    selected_symbols = {item["symbol"] for item in selected}
    for symbol in sorted(PINNED):
        if symbol in by_symbol and symbol not in selected_symbols:
            selected.append(by_symbol[symbol])
    return selected


def chart_data(symbol: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(yahoo_symbol(symbol))
    query = urllib.parse.urlencode(
        {"range": "2y", "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    )
    payload = fetch_json(f"{YAHOO_CHART.format(symbol=encoded)}?{query}")
    result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise ValueError("empty chart response")
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0])
    adjusted = (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    raw_closes = adjusted or quote.get("close") or []
    raw_volumes = quote.get("volume") or []
    closes: list[float] = []
    volumes: list[float | None] = []
    for index, raw_close in enumerate(raw_closes):
        close = number(raw_close)
        if close is None or close <= 0:
            continue
        closes.append(close)
        volumes.append(number(raw_volumes[index]) if index < len(raw_volumes) else None)
    if len(closes) < 60:
        raise ValueError("insufficient price history")
    meta = result.get("meta") or {}
    latest_volume = volumes[-1] if volumes else None
    baseline_volume = mean(volumes[-21:-1]) if len(volumes) >= 21 else mean(volumes[:-1])
    daily_logs = [math.log(closes[i] / closes[i - 1]) for i in range(max(1, len(closes) - 20), len(closes))]
    volatility = statistics.pstdev(daily_logs) * math.sqrt(252) * 100 if len(daily_logs) > 2 else None
    high_52 = max(closes[-252:])
    ma20 = mean(closes[-20:])
    ma50 = mean(closes[-50:])
    ma200 = mean(closes[-200:]) if len(closes) >= 200 else None
    price = closes[-1]
    return {
        "price": rounded(price),
        "currency": meta.get("currency") or "USD",
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName") or "",
        "lastMarketTime": meta.get("regularMarketTime"),
        "ret1": rounded(change(closes, 1)),
        "ret5": rounded(change(closes, 5)),
        "ret20": rounded(change(closes, 20)),
        "ret60": rounded(change(closes, 60)),
        "ret120": rounded(change(closes, 120)),
        "ret252": rounded(change(closes, 252)),
        "volumeRatio": rounded(latest_volume / baseline_volume if latest_volume and baseline_volume else None),
        "volatility20": rounded(volatility),
        "distMa20": rounded(pct(price, ma20)),
        "distMa50": rounded(pct(price, ma50)),
        "distMa200": rounded(pct(price, ma200)),
        "fromHigh52": rounded(pct(price, high_52)),
        "sparkline": [rounded(value, 3) for value in closes[-60:]],
        "_ma20": ma20,
        "_ma50": ma50,
        "_ma200": ma200,
    }


def series_values(payload: dict[str, Any]) -> dict[str, list[tuple[str, float]]]:
    output: dict[str, list[tuple[str, float]]] = {}
    results = ((payload or {}).get("timeseries") or {}).get("result") or []
    for result in results:
        metric_types = (result.get("meta") or {}).get("type") or []
        if not metric_types:
            continue
        metric = metric_types[0]
        points: list[tuple[str, float]] = []
        for point in result.get(metric) or []:
            raw = ((point.get("reportedValue") or {}).get("raw"))
            value = number(raw)
            as_of = str(point.get("asOfDate") or "")
            if value is not None and as_of:
                points.append((as_of, value))
        output[metric] = sorted(points, key=lambda point: point[0])
    return output


def latest(series: dict[str, list[tuple[str, float]]], metric: str) -> float | None:
    values = series.get(metric) or []
    return values[-1][1] if values else None


def annual_values(series: dict[str, list[tuple[str, float]]], metric: str) -> list[float]:
    return [value for _, value in (series.get(metric) or [])]


def fundamental_data(symbol: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(yahoo_symbol(symbol))
    end = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    start = int((datetime.now(timezone.utc) - timedelta(days=365 * 6)).timestamp())
    query = urllib.parse.urlencode(
        {
            "symbol": yahoo_symbol(symbol),
            "type": ",".join(FUNDAMENTAL_TYPES),
            "period1": start,
            "period2": end,
        },
        safe=",",
    )
    payload = fetch_json(f"{YAHOO_FUNDAMENTALS.format(symbol=encoded)}?{query}")
    series = series_values(payload)
    revenues = annual_values(series, "annualTotalRevenue")
    eps = annual_values(series, "annualDilutedEPS")
    revenue = latest(series, "trailingTotalRevenue") or (revenues[-1] if revenues else None)
    net_income = latest(series, "trailingNetIncome") or latest(series, "annualNetIncome")
    operating_income = latest(series, "trailingOperatingIncome") or latest(series, "annualOperatingIncome")
    free_cash_flow = latest(series, "trailingFreeCashFlow") or latest(series, "annualFreeCashFlow")
    equity = latest(series, "annualStockholdersEquity")
    debt = latest(series, "annualTotalDebt")
    invested_capital = latest(series, "annualInvestedCapital")
    ebit = latest(series, "annualEBIT")
    revenue_growth = pct(revenues[-1], revenues[-2]) if len(revenues) >= 2 else None
    revenue_cagr3 = cagr(revenues[-1], revenues[-4], 3) if len(revenues) >= 4 else None
    eps_growth = None
    if len(eps) >= 2 and eps[-2] > 0 and eps[-1] > 0:
        eps_growth = pct(eps[-1], eps[-2])
    return {
        "revenueGrowth": rounded(revenue_growth),
        "revenueCagr3": rounded(revenue_cagr3),
        "epsGrowth": rounded(eps_growth),
        "netMargin": rounded((net_income / revenue * 100) if net_income is not None and revenue else None),
        "operatingMargin": rounded((operating_income / revenue * 100) if operating_income is not None and revenue else None),
        "fcfMargin": rounded((free_cash_flow / revenue * 100) if free_cash_flow is not None and revenue else None),
        "roic": rounded((ebit * 0.79 / invested_capital * 100) if ebit is not None and invested_capital and invested_capital > 0 else None),
        "debtEquity": rounded((debt / equity) if debt is not None and equity and equity > 0 else None),
        "pe": rounded(latest(series, "trailingPeRatio")),
        "ps": rounded(latest(series, "trailingPsRatio")),
        "reportedMarketCap": rounded(latest(series, "trailingMarketCap"), 0),
    }


def collect(item: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    row = dict(item)
    errors: list[str] = []
    try:
        row.update(chart_data(item["symbol"]))
    except Exception as exc:
        errors.append(f"{item['symbol']} price: {type(exc).__name__}")
    try:
        row.update(fundamental_data(item["symbol"]))
    except Exception as exc:
        errors.append(f"{item['symbol']} fundamentals: {type(exc).__name__}")
    return row, errors


def percentile(value: float | None, population: list[float], *, inverse: bool = False) -> float | None:
    if value is None or not population:
        return None
    ordered = sorted(population)
    below = sum(1 for candidate in ordered if candidate < value)
    equal = sum(1 for candidate in ordered if candidate == value)
    rank = (below + max(0, equal - 1) / 2) / max(1, len(ordered) - 1)
    score = rank * 100
    return 100 - score if inverse else score


def weighted_score(parts: list[tuple[float | None, float]], *, minimum_parts: int = 3) -> float | None:
    present = [(value, weight) for value, weight in parts if value is not None]
    if len(present) < minimum_parts:
        return None
    total_weight = sum(weight for _, weight in present)
    return sum(float(value) * weight for value, weight in present) / total_weight


def stage_for(row: dict[str, Any]) -> str:
    price, ma20, ma50, ma200 = row.get("price"), row.get("_ma20"), row.get("_ma50"), row.get("_ma200")
    if all(value is not None for value in (price, ma20, ma50, ma200)):
        if price > ma20 > ma50 > ma200:
            return "主升"
        if price > ma50 > ma200:
            return "上升"
        if price < ma20 < ma50 < ma200:
            return "下行"
    return "整理"


def label_momentum(score: float | None, ret20: float | None) -> str:
    if score is None:
        return "数据不足"
    if score >= 80 and (ret20 or 0) > 0:
        return "强势"
    if score >= 65:
        return "偏强"
    if score >= 45:
        return "中性"
    if score >= 30:
        return "转弱"
    return "弱势"


def label_fundamental(score: float | None) -> str:
    if score is None:
        return "数据不足"
    if score >= 75:
        return "高质量扩张"
    if score >= 60:
        return "稳健增长"
    if score >= 45:
        return "中性观察"
    return "基本面承压"


def add_scores(rows: list[dict[str, Any]], benchmark: dict[str, Any]) -> None:
    metrics = [
        "ret20", "ret60", "ret120", "ret252", "volumeRatio", "distMa50",
        "revenueGrowth", "revenueCagr3", "epsGrowth", "netMargin", "fcfMargin", "roic", "debtEquity", "pe",
    ]
    populations = {
        metric: [float(row[metric]) for row in rows if row.get(metric) is not None]
        for metric in metrics
    }
    benchmark_20 = benchmark.get("ret20") or 0
    benchmark_60 = benchmark.get("ret60") or 0
    relative_population = [
        float(row.get("ret20") or 0) - benchmark_20 for row in rows if row.get("ret20") is not None
    ]
    for row in rows:
        row["relative20"] = rounded((row.get("ret20") - benchmark_20) if row.get("ret20") is not None else None)
        row["relative60"] = rounded((row.get("ret60") - benchmark_60) if row.get("ret60") is not None else None)
        row["stage"] = stage_for(row)
        trend_alignment = {
            "主升": 100,
            "上升": 78,
            "整理": 45,
            "下行": 10,
        }[row["stage"]]
        momentum = weighted_score(
            [
                (percentile(row.get("ret20"), populations["ret20"]), 22),
                (percentile(row.get("ret60"), populations["ret60"]), 22),
                (percentile(row.get("ret120"), populations["ret120"]), 18),
                (percentile(row.get("ret252"), populations["ret252"]), 14),
                (percentile(row.get("relative20"), relative_population), 12),
                (percentile(row.get("volumeRatio"), populations["volumeRatio"]), 5),
                (trend_alignment, 7),
            ]
        )
        row["momentumScore"] = rounded(momentum, 1)
        row["signal"] = label_momentum(momentum, row.get("ret20"))
        fundamentals = weighted_score(
            [
                (percentile(row.get("revenueGrowth"), populations["revenueGrowth"]), 20),
                (percentile(row.get("revenueCagr3"), populations["revenueCagr3"]), 15),
                (percentile(row.get("epsGrowth"), populations["epsGrowth"]), 15),
                (percentile(row.get("fcfMargin"), populations["fcfMargin"]), 15),
                (percentile(row.get("roic"), populations["roic"]), 15),
                (percentile(row.get("netMargin"), populations["netMargin"]), 8),
                (percentile(row.get("debtEquity"), populations["debtEquity"], inverse=True), 5),
                (percentile(row.get("pe"), [v for v in populations["pe"] if v > 0], inverse=True) if (row.get("pe") or 0) > 0 else None, 4),
                (percentile(row.get("ret20"), populations["ret20"]), 3),
            ],
            minimum_parts=4,
        )
        row["fundamentalScore"] = rounded(fundamentals, 1)
        row["fundamentalStatus"] = label_fundamental(fundamentals)


def previous_ranks() -> tuple[dict[str, int], dict[str, int]]:
    try:
        old = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}
    return (
        {row["symbol"]: row.get("momentumRank") for row in old.get("rows", []) if row.get("momentumRank")},
        {row["symbol"]: row.get("fundamentalRank") for row in old.get("rows", []) if row.get("fundamentalRank")},
    )


def rank_rows(rows: list[dict[str, Any]]) -> None:
    old_momentum, old_fundamental = previous_ranks()
    momentum = sorted(
        (row for row in rows if row.get("momentumScore") is not None),
        key=lambda row: (row["momentumScore"], row.get("ret20") or -999),
        reverse=True,
    )
    fundamentals = sorted(
        (row for row in rows if row.get("fundamentalScore") is not None),
        key=lambda row: (row["fundamentalScore"], row.get("revenueGrowth") or -999),
        reverse=True,
    )
    for rank, row in enumerate(momentum, 1):
        row["momentumRank"] = rank
        old = old_momentum.get(row["symbol"])
        row["momentumRankChange"] = old - rank if old else None
    for rank, row in enumerate(fundamentals, 1):
        row["fundamentalRank"] = rank
        old = old_fundamental.get(row["symbol"])
        row["fundamentalRankChange"] = old - rank if old else None


def clean_internal_fields(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        for key in list(row):
            if key.startswith("_"):
                del row[key]
        row["marketCap"] = rounded(row.get("marketCap"), 0)


def update_history(payload: dict[str, Any]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        history = {"snapshots": []}
    snapshot = {
        "date": payload["asOf"],
        "generatedAt": payload["generatedAt"],
        "topMomentum": [
            {"symbol": row["symbol"], "rank": row["momentumRank"], "score": row["momentumScore"]}
            for row in sorted(payload["rows"], key=lambda row: row.get("momentumRank") or 9999)[:20]
        ],
        "topFundamental": [
            {"symbol": row["symbol"], "rank": row["fundamentalRank"], "score": row["fundamentalScore"]}
            for row in sorted(payload["rows"], key=lambda row: row.get("fundamentalRank") or 9999)[:20]
        ],
    }
    snapshots = [item for item in history.get("snapshots", []) if item.get("date") != snapshot["date"]]
    snapshots.append(snapshot)
    history["snapshots"] = sorted(snapshots, key=lambda item: item.get("date", ""))[-120:]
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the public-data momentum dashboard")
    parser.add_argument("--max-symbols", type=int, default=int(os.getenv("MOMENTUM_MAX_SYMBOLS", DEFAULT_SYMBOLS)))
    parser.add_argument("--workers", type=int, default=int(os.getenv("MOMENTUM_WORKERS", DEFAULT_WORKERS)))
    args = parser.parse_args()
    if args.max_symbols < 20 or args.max_symbols > 500:
        parser.error("--max-symbols must be between 20 and 500")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    generated = datetime.now(timezone.utc)
    universe = load_universe(args.max_symbols)
    benchmark = chart_data(BENCHMARK)
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(collect, item): item["symbol"] for item in universe}
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            symbol = futures[future]
            try:
                row, row_errors = future.result()
                if row.get("price") is not None:
                    rows.append(row)
                errors.extend(row_errors)
            except Exception as exc:
                errors.append(f"{symbol}: {type(exc).__name__}")
            if completed % 25 == 0 or completed == len(futures):
                print(f"Collected {completed}/{len(futures)} symbols", flush=True)

    add_scores(rows, benchmark)
    rank_rows(rows)
    rows.sort(key=lambda row: row.get("momentumRank") or 9999)
    clean_internal_fields(rows)
    latest_market_times = [row.get("lastMarketTime") for row in rows if row.get("lastMarketTime")]
    market_time = max(latest_market_times) if latest_market_times else int(generated.timestamp())
    try:
        market_timezone = ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:  # Windows Python may not bundle IANA tzdata
        market_timezone = timezone.utc
    as_of = datetime.fromtimestamp(market_time, market_timezone).date().isoformat()
    fundamentals_covered = sum(1 for row in rows if row.get("fundamentalScore") is not None)
    payload = {
        "version": generated.strftime("%Y%m%d%H%M%S"),
        "generatedAt": generated.isoformat(timespec="seconds"),
        "asOf": as_of,
        "universe": {
            "requested": len(universe),
            "screened": len(rows),
            "minimumMarketCap": 500_000_000,
            "description": "Nasdaq 股票筛选器中按市值排序的大盘及高流动性美股，并补充重点观察标的",
        },
        "benchmark": {
            "symbol": BENCHMARK,
            "ret20": benchmark.get("ret20"),
            "ret60": benchmark.get("ret60"),
        },
        "coverage": {
            "price": len(rows),
            "fundamentals": fundamentals_covered,
            "warnings": len(errors),
        },
        "methodology": {
            "momentum": "20/60/120/252 日收益、相对 SPY 强弱、成交量变化与均线结构的横截面百分位综合分",
            "fundamental": "已报告收入增速、EPS 增速、利润率、自由现金流率、近似 ROIC、杠杆、估值与价格趋势的横截面综合分",
            "notice": "仅供研究与筛选，不构成投资建议；数据为公开来源的自动化计算，盘中价格和财务口径可能存在延迟。",
        },
        "sources": [
            {"name": "Nasdaq Stock Screener", "url": "https://www.nasdaq.com/market-activity/stocks/screener"},
            {"name": "Yahoo Finance Chart", "url": "https://finance.yahoo.com/"},
            {"name": "Yahoo Finance Fundamentals Timeseries", "url": "https://finance.yahoo.com/"},
        ],
        "rows": rows,
        "warnings": errors[:40],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    update_history(payload)
    print(
        f"OK: {len(rows)} equities, {fundamentals_covered} fundamental profiles -> {OUTPUT_PATH} "
        f"(as of {as_of}, {len(errors)} warnings)"
    )
    return 0 if len(rows) >= min(20, args.max_symbols) else 1


if __name__ == "__main__":
    raise SystemExit(main())
