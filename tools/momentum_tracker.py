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
SCHEMA_PATH = ROOT / "tools" / "momentum_schema.json"
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
DEFAULT_SYMBOLS = 500
DEFAULT_WORKERS = 12
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
    "trailingForwardPeRatio",
    "trailingPsRatio",
    "trailingMarketCap",
    "trailingEnterprisesValueRevenueRatio",
    "trailingEnterprisesValueEBITDARatio",
    "trailingEnterpriseValue",
    "quarterlyTotalRevenue",
    "quarterlyNetIncome",
    "quarterlyOperatingIncome",
    "quarterlyFreeCashFlow",
    "quarterlyDilutedEPS",
    "quarterlyStockholdersEquity",
    "quarterlyTotalDebt",
    "quarterlyInvestedCapital",
    "quarterlyEBIT",
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
    volume_5 = mean(volumes[-5:])
    volume_20 = mean(volumes[-20:])
    consecutive_volume = 0
    if volume_20:
        for value in reversed(volumes):
            if value is not None and value > volume_20:
                consecutive_volume += 1
            else:
                break
    daily_logs = [math.log(closes[i] / closes[i - 1]) for i in range(max(1, len(closes) - 20), len(closes))]
    volatility = statistics.pstdev(daily_logs) * math.sqrt(252) * 100 if len(daily_logs) > 2 else None
    recent_logs = [math.log(closes[i] / closes[i - 1]) for i in range(max(1, len(closes) - 10), len(closes))]
    long_logs = [math.log(closes[i] / closes[i - 1]) for i in range(max(1, len(closes) - 60), len(closes))]
    recent_vol = statistics.pstdev(recent_logs) if len(recent_logs) > 2 else None
    long_vol = statistics.pstdev(long_logs) if len(long_logs) > 2 else None
    volatility_ratio = recent_vol / long_vol if recent_vol is not None and long_vol else None
    if volatility_ratio is None:
        volatility_state = "数据不足"
    elif volatility_ratio >= 1.25:
        volatility_state = "扩张"
    elif volatility_ratio <= 0.75:
        volatility_state = "压缩"
    else:
        volatility_state = "正常"
    band_widths: list[float] = []
    for offset in range(min(120, len(closes) - 19)):
        end = len(closes) - offset
        window = closes[end - 20:end]
        window_mean = mean(window)
        if window_mean:
            band_widths.append(statistics.pstdev(window) / window_mean)
    current_band = band_widths[0] if band_widths else None
    sorted_bands = sorted(band_widths)
    squeeze_cutoff = sorted_bands[max(0, int(len(sorted_bands) * 0.2) - 1)] if sorted_bands else None
    bollinger_state = "压缩" if current_band is not None and squeeze_cutoff is not None and current_band <= squeeze_cutoff else "正常"
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
        "volumeRatio5": rounded(volume_5 / volume_20 if volume_5 and volume_20 else None),
        "consecutiveVolume": consecutive_volume,
        "volatility20": rounded(volatility),
        "bollingerState": bollinger_state,
        "volatilityState": volatility_state,
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
    start = int((datetime.now(timezone.utc) - timedelta(days=365 * 10)).timestamp())
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
    quarterly_revenues = annual_values(series, "quarterlyTotalRevenue")
    quarterly_operating = annual_values(series, "quarterlyOperatingIncome")
    quarterly_fcf = annual_values(series, "quarterlyFreeCashFlow")
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
    revenue_cagr5 = cagr(revenues[-1], revenues[-6], 5) if len(revenues) >= 6 else None
    eps_growth = None
    if len(eps) >= 2 and eps[-2] > 0 and eps[-1] > 0:
        eps_growth = pct(eps[-1], eps[-2])
    quarterly_yoy = pct(quarterly_revenues[-1], quarterly_revenues[-5]) if len(quarterly_revenues) >= 5 else None
    quarterly_qoq = pct(quarterly_revenues[-1], quarterly_revenues[-2]) if len(quarterly_revenues) >= 2 else None
    current_op_margin = (
        quarterly_operating[-1] / quarterly_revenues[-1] * 100
        if quarterly_operating and quarterly_revenues and quarterly_revenues[-1]
        else None
    )
    previous_op_margin = (
        quarterly_operating[-2] / quarterly_revenues[-2] * 100
        if len(quarterly_operating) >= 2 and len(quarterly_revenues) >= 2 and quarterly_revenues[-2]
        else None
    )
    margin_change = (
        current_op_margin - previous_op_margin
        if current_op_margin is not None and previous_op_margin is not None
        else None
    )
    if quarterly_yoy is None:
        quarterly_trend = "季度趋势未覆盖"
    elif quarterly_yoy >= 20 and (quarterly_qoq or 0) > 0 and (margin_change or 0) >= 0:
        quarterly_trend = "加速增长"
    elif quarterly_yoy >= 10 and (margin_change or 0) >= -1:
        quarterly_trend = "平稳"
    elif quarterly_yoy > 0:
        quarterly_trend = "增速放缓"
    else:
        quarterly_trend = "趋势恶化"
    return {
        "revenueGrowth": rounded(revenue_growth),
        "revenueCagr3": rounded(revenue_cagr3),
        "revenueCagr5": rounded(revenue_cagr5),
        "epsGrowth": rounded(eps_growth),
        "netMargin": rounded((net_income / revenue * 100) if net_income is not None and revenue else None),
        "operatingMargin": rounded((operating_income / revenue * 100) if operating_income is not None and revenue else None),
        "fcfMargin": rounded((free_cash_flow / revenue * 100) if free_cash_flow is not None and revenue else None),
        "roic": rounded((ebit * 0.79 / invested_capital * 100) if ebit is not None and invested_capital and invested_capital > 0 else None),
        "debtEquity": rounded((debt / equity) if debt is not None and equity and equity > 0 else None),
        "pe": rounded(latest(series, "trailingPeRatio")),
        "forwardPe": rounded(latest(series, "trailingForwardPeRatio")),
        "ps": rounded(latest(series, "trailingPsRatio")),
        "evSales": rounded(latest(series, "trailingEnterprisesValueRevenueRatio")),
        "evEbitda": rounded(latest(series, "trailingEnterprisesValueEBITDARatio")),
        "enterpriseValue": rounded(latest(series, "trailingEnterpriseValue"), 0),
        "quarterlyRevenueYoy": rounded(quarterly_yoy),
        "quarterlyRevenueQoq": rounded(quarterly_qoq),
        "quarterlyMarginChange": rounded(margin_change),
        "quarterlyFcf": rounded(quarterly_fcf[-1], 0) if quarterly_fcf else None,
        "quarterlyTrend": quarterly_trend,
        "_trailingFcf": free_cash_flow,
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


def investment_profile(row: dict[str, Any]) -> str:
    growth = row.get("revenueGrowth") or row.get("revenueCagr3") or 0
    quality = row.get("fundamentalScore") or 0
    market_cap = row.get("marketCap") or 0
    fcf_margin = row.get("fcfMargin") or 0
    roic = row.get("roic") or 0
    if market_cap < 10_000_000_000 and growth >= 20:
        return "小市值成长"
    if growth >= 20 and quality >= 70:
        return "长期复合增长"
    if quality >= 70 and fcf_margin >= 15 and roic >= 12:
        return "优质稳健增长"
    if growth < 5 and (row.get("ret60") or 0) >= 15:
        return "周期反转"
    if fcf_margin >= 20 and growth < 12:
        return "持续现金流型"
    if (row.get("netMargin") or 0) < 0 and growth >= 25:
        return "创新颠覆"
    return "综合成长"


def movement_interpretation(row: dict[str, Any]) -> str:
    parts = []
    if row.get("relative20") is not None:
        parts.append(f"近20日相对SPY {row['relative20']:+.1f}%")
    if row.get("volumeRatio5") is not None:
        parts.append(f"5日/20日量比 {row['volumeRatio5']:.2f}x")
    parts.append(f"均线阶段为{row.get('stage', '数据不足')}")
    parts.append(f"波动率{row.get('volatilityState', '数据不足')}")
    return "；".join(parts) + "。期权链字段需授权数据源确认。"


def movement_action(row: dict[str, Any]) -> str:
    score = row.get("momentumScore") or 0
    if score >= 80 and (row.get("ret20") or 0) > 0:
        return "强趋势：优先核对催化与追涨风险"
    if score >= 65:
        return "偏强：加入持续观察"
    if score >= 45:
        return "中性：等待价格与量能确认"
    return "偏弱：暂缓，观察趋势修复"


def fill_research_fields(row: dict[str, Any]) -> None:
    momentum = row.get("momentumScore") or 0
    fundamental = row.get("fundamentalScore") or 0
    recovery_signals = sum(
        condition
        for condition in [
            (row.get("revenueGrowth") or 0) >= 15,
            (row.get("epsGrowth") or 0) >= 20,
            row.get("quarterlyTrend") in {"加速增长", "平稳"},
            (row.get("fcfMargin") or -999) >= 10,
        ]
    )
    alpha = 100 if momentum >= 75 and recovery_signals >= 2 else 65 if momentum >= 60 and recovery_signals >= 1 else 25
    risk_penalty = 0
    if (row.get("pe") or 0) > 100:
        risk_penalty += 8
    if (row.get("debtEquity") or 0) > 3:
        risk_penalty += 6
    if row.get("fcfMargin") is not None and row["fcfMargin"] < 0:
        risk_penalty += 6
    research = max(0, min(100, fundamental * 0.60 + alpha * 0.25 + momentum * 0.15 - risk_penalty))
    row["_researchScore100"] = research
    row["researchPriorityScore"] = rounded(research / 20, 1)
    row["qualityScore"] = rounded(fundamental / 20, 1) if row.get("fundamentalScore") is not None else None
    row["fcfYield"] = rounded(
        row.get("_trailingFcf") / row.get("marketCap") * 100
        if row.get("_trailingFcf") is not None and row.get("marketCap")
        else None
    )
    row["fy1RevenueGrowth"] = None
    row["fy1EpsGrowth"] = None
    row["fy2ForwardPe"] = None
    row["alphaCatalyst"] = "是" if alpha >= 65 else "否"
    if momentum >= 70 and recovery_signals >= 2:
        row["davisDouble"] = "双重确认"
    elif momentum >= 60:
        row["davisDouble"] = "价格先行复核"
    else:
        row["davisDouble"] = "未确认"
    row["expectationChange"] = None
    momentum_parts = []
    for label, key in [("近3月", "ret60"), ("近6月", "ret120"), ("近1年", "ret252")]:
        value = row.get(key)
        if value is not None and value >= 15:
            momentum_parts.append(f"{label}强势")
    row["marketMomentumHint"] = "；".join(momentum_parts) if momentum_parts else "暂无连续强动量"
    chase = []
    if (row.get("fromHigh52") or -100) > -5:
        chase.append("接近52周高位")
    if (row.get("ret20") or 0) > 20:
        chase.append("20日涨幅较快")
    if (row.get("pe") or 0) > 60:
        chase.append("估值偏高")
    row["chaseReview"] = "；".join(chase) if chase else "无明显追涨警报"
    row["investmentProfile"] = investment_profile(row)
    row["whyWatch"] = (
        f"公开数据综合分{row['researchPriorityScore']:.1f}，经营质量分"
        f"{row.get('qualityScore') if row.get('qualityScore') is not None else '—'}，"
        f"季度趋势为{row.get('quarterlyTrend', '未覆盖')}，量价信号为{row.get('signal', '数据不足')}。"
    )
    if research >= 75:
        row["watchAction"] = "重点研究"
    elif research >= 60:
        row["watchAction"] = "继续跟踪"
    elif research >= 45:
        row["watchAction"] = "等待确认"
    else:
        row["watchAction"] = "暂缓"
    risks = []
    if (row.get("pe") or 0) > 60:
        risks.append(f"P/E {row['pe']:.1f}x 偏高")
    if (row.get("debtEquity") or 0) > 2:
        risks.append(f"负债权益比 {row['debtEquity']:.1f}x")
    if row.get("fcfMargin") is not None and row["fcfMargin"] < 0:
        risks.append("自由现金流率为负")
    if row.get("quarterlyTrend") == "趋势恶化":
        risks.append("季度趋势恶化")
    row["riskReview"] = "；".join(risks) if risks else "未触发公开数据规则警报"
    row["currentStatus"] = "重点研究" if research >= 75 else "继续跟踪" if research >= 55 else "观察"
    row["rsSignal"] = "强于大盘" if (row.get("relative20") or 0) >= 5 else "跑输大盘" if (row.get("relative20") or 0) <= -5 else "接近大盘"
    row["resonance"] = "现货确认·待期权" if momentum >= 65 else "待确认"
    row["spotScore"] = rounded(momentum, 1)
    row["interpretation"] = movement_interpretation(row)
    row["movementAction"] = movement_action(row)


def add_scores(rows: list[dict[str, Any]], benchmark: dict[str, Any]) -> None:
    metrics = [
        "ret20", "ret60", "ret120", "ret252", "volumeRatio", "distMa50",
        "revenueGrowth", "revenueCagr3", "epsGrowth", "netMargin", "fcfMargin", "roic", "debtEquity", "pe",
    ]
    populations = {
        metric: [float(row[metric]) for row in rows if row.get(metric) is not None]
        for metric in metrics
    }
    sector_populations = {
        (sector, metric): [
            float(row[metric])
            for row in rows
            if row.get("sector") == sector and row.get(metric) is not None
        ]
        for sector in {row.get("sector") for row in rows}
        for metric in metrics
    }

    def quality_percentile(row: dict[str, Any], metric: str, *, inverse: bool = False) -> float | None:
        peers = sector_populations.get((row.get("sector"), metric), [])
        population = peers if len(peers) >= 5 else populations[metric]
        if metric == "pe":
            population = [value for value in population if value > 0]
        value = row.get(metric)
        if metric == "pe" and (value or 0) <= 0:
            return None
        return percentile(value, population, inverse=inverse)
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
                (quality_percentile(row, "revenueGrowth"), 20),
                (quality_percentile(row, "revenueCagr3"), 15),
                (quality_percentile(row, "epsGrowth"), 15),
                (quality_percentile(row, "fcfMargin"), 15),
                (quality_percentile(row, "roic"), 15),
                (quality_percentile(row, "netMargin"), 8),
                (quality_percentile(row, "debtEquity", inverse=True), 5),
                (quality_percentile(row, "pe", inverse=True), 4),
                (percentile(row.get("ret20"), populations["ret20"]), 3),
            ],
            minimum_parts=4,
        )
        row["fundamentalScore"] = rounded(fundamentals, 1)
        row["fundamentalStatus"] = label_fundamental(fundamentals)
        fill_research_fields(row)


def previous_ranks() -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    try:
        old = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}, {}
    return (
        {row["symbol"]: row.get("momentumRank") for row in old.get("rows", []) if row.get("momentumRank")},
        {row["symbol"]: row.get("fundamentalRank") for row in old.get("rows", []) if row.get("fundamentalRank")},
        {row["symbol"]: row.get("researchPriorityRank") for row in old.get("rows", []) if row.get("researchPriorityRank")},
    )


def rank_rows(rows: list[dict[str, Any]]) -> None:
    old_momentum, old_fundamental, old_research = previous_ranks()
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
    research = sorted(
        (row for row in rows if row.get("_researchScore100") is not None),
        key=lambda row: (row["_researchScore100"], row.get("fundamentalScore") or -999),
        reverse=True,
    )
    for rank, row in enumerate(momentum, 1):
        row["momentumRank"] = rank
        old = old_momentum.get(row["symbol"])
        row["momentumRankChange"] = old - rank if old else None
    for rank, row in enumerate(fundamentals, 1):
        row["fundamentalRank"] = rank
        row["sectorQualityRank"] = rank
        old = old_fundamental.get(row["symbol"])
        row["fundamentalRankChange"] = old - rank if old else None
    for rank, row in enumerate(research, 1):
        row["researchPriorityRank"] = rank
        old = old_research.get(row["symbol"])
        row["researchPriorityRankChange"] = old - rank if old else None


def load_history() -> dict[str, Any]:
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"snapshots": []}


def add_tracking_fields(rows: list[dict[str, Any]], as_of: str) -> None:
    snapshots = load_history().get("snapshots", [])
    for row in rows:
        symbol = row["symbol"]
        seen_dates = []
        for snapshot in snapshots:
            members = snapshot.get("members") or snapshot.get("topMomentum") or []
            if any(member.get("symbol") == symbol for member in members):
                seen_dates.append(snapshot.get("date"))
        dates = sorted(value for value in seen_dates if value)
        row["firstDetected"] = dates[0] if dates else as_of
        age = len(set(dates + [as_of]))
        row["signalAge"] = f"新信号(第1天)" if age == 1 else f"持续跟踪(第{age}天)"


def ensure_schema_fields(rows: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    keys = {
        column["key"]
        for section in (schema.get("tenx", {}), schema.get("movement", {}))
        for column in section.get("columns", [])
    }
    for row in rows:
        for key in keys:
            row.setdefault(key, None)


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
        "members": [
            {
                "symbol": row["symbol"],
                "rank": row.get("momentumRank"),
                "score": row.get("momentumScore"),
                "signal": row.get("signal"),
            }
            for row in payload["rows"]
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
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
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
    rows.sort(key=lambda row: row.get("researchPriorityRank") or 9999)
    latest_market_times = [row.get("lastMarketTime") for row in rows if row.get("lastMarketTime")]
    market_time = max(latest_market_times) if latest_market_times else int(generated.timestamp())
    try:
        market_timezone = ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:  # Windows Python may not bundle IANA tzdata
        market_timezone = timezone.utc
    as_of = datetime.fromtimestamp(market_time, market_timezone).date().isoformat()
    add_tracking_fields(rows, as_of)
    ensure_schema_fields(rows, schema)
    clean_internal_fields(rows)
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
        "schemas": schema,
        "methodology": {
            "tenx": "公开版研究优先级采用已报告经营质量、季度趋势、Alpha恢复信号与连续市场动量组合，并对高估值、高杠杆和负自由现金流做复核扣分。经营质量关注增长、利润率、自由现金流、资本回报与财务强度。",
            "movement": "公开版动量分采用20/60/120/252日收益、相对SPY强弱、5日/20日量能、均线结构、布林带与波动率状态。期权链、Gamma、Reddit和分析师周度快照字段完整保留，但在获得合规授权数据源前不生成数值。",
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
