#!/usr/bin/env python3
"""Build the public-data cross-asset returns & volatility tracker for the static site.

Dependency-free (stdlib only) so it can run on GitHub Actions, mirroring the
design of tools/momentum_tracker.py: pulls free Yahoo Finance chart data for a
fixed universe of liquid, long-history proxy instruments (one per asset class),
computes calendar-year total returns plus annual/monthly/daily volatility, and
writes a compact dashboard payload for the site plus an appended history
snapshot.

Two asset classes (hedge funds, private equity) have no free daily-priced
proxy with real fund-level data, so their *index-level* annual returns are
merged in from a hand-maintained, fully-cited static file
(data/asset_tracker/curated_sources.json) rather than computed from price
history. Listed ETF proxies for those two classes are tracked separately and
labelled explicitly as proxies, not the real index.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "docs" / "asset_tracker.json"
HISTORY_PATH = ROOT / "data" / "asset_tracker" / "history.json"
CURATED_PATH = ROOT / "data" / "asset_tracker" / "curated_sources.json"

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 "
    "P-investing-asset-tracker/1.0"
)
TIMEOUT = 45
MAX_ANNUAL_YEARS = 30    # 年度收益率/年度波动率窗口
MONTHLY_VOL_YEARS = 10   # 月度波动率回看窗口（也是月度相关性回看窗口）
DAILY_VOL_YEARS = 5      # 日度波动率回看窗口
MIN_MONTHLY_OVERLAP = 24 # 月度相关性最少重叠月数，不足则该对资产标注数据不足
MIN_ANNUAL_OVERLAP = 5   # 年度相关性最少重叠年数

# 资产类别 -> 可自动抓取的代理标的（流动性最好、历史最长的公开上市工具）
UNIVERSE: list[dict[str, str]] = [
    {"id": "cash", "category": "现金/短期流动性", "name": "现金收益率（美国1-3月期国库券，BIL代理）",
     "symbol": "BIL", "note": "ETF成立于2007年5月，早于此的现金收益率需参考美国财政部3个月期国库券利率(DGS3MO)等官方利率序列。"},
    {"id": "us_treasury", "category": "政府债券", "name": "美国国债（7-10年期，IEF代理）",
     "symbol": "IEF", "note": "ETF成立于2002年7月。"},
    {"id": "us_ig_credit", "category": "公司债券", "name": "美国投资级企业债（LQD代理）",
     "symbol": "LQD", "note": "ETF成立于2002年7月。"},
    {"id": "us_equity", "category": "二级市场股权", "name": "美股（标普500指数，价格回报，不含股息再投资）",
     "symbol": "^GSPC", "note": "指数历史可回溯至1927年；本追踪器仅为价格指数，未计入股息，实际含股息总回报高于本表数字。"},
    {"id": "europe_equity", "category": "二级市场股权", "name": "欧股（EURO STOXX 50指数，价格回报）",
     "symbol": "^STOXX50E", "note": "指数历史可回溯至1986年；同样为价格指数，不含股息。"},
    {"id": "asia_equity", "category": "二级市场股权", "name": "亚洲股票（日经225指数，价格回报）",
     "symbol": "^N225", "note": "指数历史可回溯至1965年；价格指数，不含股息；作为亚洲发达市场代表，非全亚洲综合指数。"},
    {"id": "global_equity", "category": "二级市场股权", "name": "全球股票（MSCI ACWI全球指数，ACWI ETF代理，含股息）",
     "symbol": "ACWI", "note": "ETF成立于2008年3月，历史不足30年，已在输出中如实标注起始年份。"},
    {"id": "private_equity_proxy", "category": "一级市场私募股权（上市代理）", "name": "私募股权（上市另类资管组合，PSP代理）",
     "symbol": "PSP", "note": "ETF成立于2006年10月；追踪上市私募股权公司股价，并非真实私募基金净值回报(IRR/TVPI)，仅作流动性代理，请同时参考curated真实PE指数。"},
    {"id": "hedge_fund_proxy", "category": "对冲基金（上市代理）", "name": "对冲基金（多策略流动性另类ETF，QAI代理）",
     "symbol": "QAI", "note": "ETF成立于2009年3月；为流动性另类复制策略，收益特征与真实对冲基金指数（HFRI）存在差异，仅作参考，请同时参考curated真实HFRI指数。"},
    {"id": "commodities", "category": "大宗商品", "name": "大宗商品综合（DBC代理）",
     "symbol": "DBC", "note": "ETF成立于2006年2月。"},
    {"id": "gold", "category": "大宗商品", "name": "黄金（COMEX黄金期货连续合约）",
     "symbol": "GC=F", "note": "Yahoo Finance连续合约数据通常可回溯至2000年附近。"},
    {"id": "oil", "category": "大宗商品", "name": "原油（WTI原油期货连续合约）",
     "symbol": "CL=F", "note": "Yahoo Finance连续合约数据通常可回溯至2000年附近。"},
    {"id": "bitcoin", "category": "加密资产", "name": "比特币",
     "symbol": "BTC-USD", "note": "可靠交易所定价数据仅自2014年附近起，历史远不足30年。"},
]


def fetch_json(url: str) -> Any:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Cache-Control": "no-cache",
    }
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # network hiccups / throttling
            last_error = exc
            if attempt < 3:
                time.sleep((1.3**attempt) + random.random())
    assert last_error is not None
    raise last_error


def fetch_series(symbol: str, rng: str, interval: str) -> tuple[list[datetime], list[float]]:
    """Fetch (dates, closes) for an explicit, bounded range+interval.

    IMPORTANT: Yahoo's chart API silently downsamples (serves far fewer bars
    than requested) when `range="max"` is combined with a long history —
    e.g. a 42-year daily request for ^GSPC came back with only ~169 points
    (effectively quarterly), which would massively overstate volatility if
    treated as daily/monthly data. Always pass an explicit, bounded numeric
    range (e.g. "35y", "5y") instead of "max"; verified empirically to return
    the correct point count (days-per-year * years, or months * years+1).
    """
    encoded = urllib.parse.quote(symbol)
    query = urllib.parse.urlencode(
        {"range": rng, "interval": interval, "events": "div,splits", "includeAdjustedClose": "true"}
    )
    payload = fetch_json(f"{YAHOO_CHART.format(symbol=encoded)}?{query}")
    result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise ValueError(f"empty chart response for {symbol} ({rng}/{interval})")
    timestamps = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0])
    adjusted = (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    raw_closes = adjusted or quote.get("close") or []
    dates: list[datetime] = []
    closes: list[float] = []
    for ts, raw_close in zip(timestamps, raw_closes):
        if raw_close is None or raw_close <= 0:
            continue
        dates.append(datetime.fromtimestamp(ts, tz=timezone.utc))
        closes.append(float(raw_close))
    if len(closes) < 10:
        raise ValueError(f"insufficient price history for {symbol} ({rng}/{interval}, {len(closes)} points)")
    return dates, closes


def year_end_closes(dates: list[datetime], closes: list[float]) -> dict[int, float]:
    """Last available close of each calendar year -> year-end price (incl. current YTD year)."""
    out: dict[int, float] = {}
    for d, c in zip(dates, closes):
        out[d.year] = c  # relies on chronological order; later entries overwrite
    return out


def month_end_closes(dates: list[datetime], closes: list[float]) -> list[float]:
    buckets: dict[tuple[int, int], float] = {}
    for d, c in zip(dates, closes):
        buckets[(d.year, d.month)] = c
    return [buckets[k] for k in sorted(buckets.keys())]


def month_end_closes_keyed(dates: list[datetime], closes: list[float]) -> dict[str, float]:
    buckets: dict[tuple[int, int], float] = {}
    for d, c in zip(dates, closes):
        buckets[(d.year, d.month)] = c
    return {f"{y:04d}-{m:02d}": buckets[(y, m)] for (y, m) in sorted(buckets.keys())}


def monthly_return_map(keyed_closes: dict[str, float], cutoff_months: int) -> dict[str, float]:
    """Month-over-month % returns, keyed by the *later* month's 'YYYY-MM', capped to the trailing window."""
    keys = sorted(keyed_closes.keys())[-(cutoff_months + 1):]
    out: dict[str, float] = {}
    for i in range(1, len(keys)):
        prev, cur = keyed_closes[keys[i - 1]], keyed_closes[keys[i]]
        if prev > 0:
            out[keys[i]] = cur / prev - 1.0
    return out


def pearson_correlation(pairs: list[tuple[float, float]]) -> float | None:
    n = len(pairs)
    if n < 2:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    if var_x <= 0 or var_y <= 0:
        return None
    return cov / math.sqrt(var_x * var_y)


def correlation_matrix(
    series_by_id: dict[str, dict[str, float]], min_overlap: int
) -> dict[str, Any]:
    ids = sorted(series_by_id.keys())
    matrix: dict[str, dict[str, Any]] = {}
    for a in ids:
        matrix[a] = {}
        for b in ids:
            if a == b:
                matrix[a][b] = {"r": 1.0, "n": len(series_by_id[a])}
                continue
            shared_keys = sorted(set(series_by_id[a]) & set(series_by_id[b]))
            n = len(shared_keys)
            if n < min_overlap:
                matrix[a][b] = {"r": None, "n": n}
                continue
            pairs = [(series_by_id[a][k], series_by_id[b][k]) for k in shared_keys]
            r = pearson_correlation(pairs)
            matrix[a][b] = {"r": round(r, 3) if r is not None else None, "n": n}
    return {"assetIds": ids, "matrix": matrix}


def pct_returns(series: list[float]) -> list[float]:
    return [(series[i] / series[i - 1] - 1.0) for i in range(1, len(series)) if series[i - 1] > 0]


def annualized_stdev(returns: list[float], periods_per_year: float) -> float | None:
    if len(returns) < 3:
        return None
    return statistics.stdev(returns) * math.sqrt(periods_per_year) * 100.0


def geometric_mean_pct(annual_returns_pct: list[float]) -> float | None:
    if not annual_returns_pct:
        return None
    product = 1.0
    for r in annual_returns_pct:
        product *= (1.0 + r / 100.0)
    if product <= 0:
        return None
    return (product ** (1.0 / len(annual_returns_pct)) - 1.0) * 100.0


def build_asset_stats(
    asset_id: str, category: str, name: str, symbol: str, note: str
) -> tuple[dict[str, Any], dict[str, float]]:
    # Monthly series (explicit bounded range) drives annual returns + monthly vol + monthly correlation.
    dates, closes = fetch_series(symbol, f"{MAX_ANNUAL_YEARS + 5}y", "1mo")
    first_year, last_year = dates[0].year, dates[-1].year

    ye = year_end_closes(dates, closes)
    years_sorted = sorted(ye.keys())
    current_year = dates[-1].year
    is_current_year_partial = dates[-1].date() < datetime(current_year, 12, 29, tzinfo=timezone.utc).date()

    annual_returns: dict[str, float] = {}
    for y in years_sorted:
        if y - 1 in ye and y in ye:
            annual_returns[str(y)] = round((ye[y] / ye[y - 1] - 1.0) * 100.0, 2)
    ytd_return = None
    complete_annual_returns = dict(annual_returns)
    if is_current_year_partial and str(current_year) in complete_annual_returns:
        ytd_return = complete_annual_returns.pop(str(current_year))

    last30_items = sorted(complete_annual_returns.items(), key=lambda kv: int(kv[0]))[-MAX_ANNUAL_YEARS:]
    last30_values = [v for _, v in last30_items]

    monthly = month_end_closes(dates, closes)
    monthly_cut = monthly[-(MONTHLY_VOL_YEARS * 12 + 1):]
    monthly_rets = pct_returns(monthly_cut)

    monthly_keyed = month_end_closes_keyed(dates, closes)
    monthly_ret_map = monthly_return_map(monthly_keyed, MONTHLY_VOL_YEARS * 12)

    daily_rets: list[float] = []
    try:
        _, daily_closes = fetch_series(symbol, f"{DAILY_VOL_YEARS}y", "1d")
        daily_rets = pct_returns(daily_closes)
    except Exception as exc:  # daily vol is best-effort; annual/monthly stats still valid
        print(f"    (no daily series for {symbol}: {exc})")

    stats = {
        "id": asset_id,
        "category": category,
        "name": name,
        "symbol": symbol,
        "note": note,
        "dataStartYear": first_year,
        "dataEndYear": last_year,
        "yearsOfAnnualData": len(last30_values),
        "latestYtdReturnPct": round(ytd_return, 2) if ytd_return is not None else None,
        "annualReturnsPct": {k: v for k, v in last30_items},
        "annualizedArithmeticMeanPct": round(statistics.fmean(last30_values), 2) if last30_values else None,
        "annualizedGeometricMeanPct": round(geometric_mean_pct(last30_values), 2) if last30_values else None,
        "annualVolatilityPct": round(statistics.stdev(last30_values), 2) if len(last30_values) >= 3 else None,
        "monthlyVolatilityAnnualizedPct": (
            round(annualized_stdev(monthly_rets, 12), 2) if monthly_rets else None
        ),
        "dailyVolatilityAnnualizedPct": (
            round(annualized_stdev(daily_rets, 252), 2) if daily_rets else None
        ),
        "monthlyVolWindowYears": MONTHLY_VOL_YEARS,
        "dailyVolWindowYears": DAILY_VOL_YEARS,
        "source": "Yahoo Finance 公开行情接口（调整后收盘价，含股息再投资的ETF除外，另有逐项说明）",
    }
    return stats, monthly_ret_map


def build_curated_asset(key: str, payload: dict[str, Any]) -> dict[str, Any]:
    annual = payload["annual_returns"]
    years_sorted = sorted(annual.keys(), key=int)
    last30 = years_sorted[-MAX_ANNUAL_YEARS:]
    values = [annual[y] for y in last30]
    missing_years = [
        str(y) for y in range(max(int(years_sorted[0]), datetime.now().year - MAX_ANNUAL_YEARS + 1),
                               datetime.now().year)
        if str(y) not in annual
    ]
    return {
        "id": key,
        "category": "对冲基金（真实指数）" if "hedge" in key else "一级市场私募股权（真实指数）",
        "name": payload["name"],
        "symbol": None,
        "note": payload.get("note", ""),
        "dataStartYear": int(years_sorted[0]),
        "dataEndYear": int(years_sorted[-1]),
        "yearsOfAnnualData": len(values),
        "latestYtdReturnPct": None,
        "annualReturnsPct": {y: annual[y] for y in last30},
        "annualizedArithmeticMeanPct": round(statistics.fmean(values), 2) if values else None,
        "annualizedGeometricMeanPct": round(geometric_mean_pct(values), 2) if values else None,
        "annualVolatilityPct": round(statistics.stdev(values), 2) if len(values) >= 3 else None,
        "monthlyVolatilityAnnualizedPct": None,
        "dailyVolatilityAnnualizedPct": None,
        "monthlyVolWindowYears": None,
        "dailyVolWindowYears": None,
        "missingYears": missing_years,
        "longTermAnnualized": payload.get("long_term_annualized_as_of_2025_06_30"),
        "source": payload["source"],
        "sourceUrls": payload.get("source_urls", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the cross-asset returns & volatility tracker")
    parser.add_argument("--only", nargs="*", default=None, help="limit to these asset ids (debug)")
    args = parser.parse_args()

    assets: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    monthly_series_by_id: dict[str, dict[str, float]] = {}

    for spec in UNIVERSE:
        if args.only and spec["id"] not in args.only:
            continue
        try:
            stats, monthly_ret_map = build_asset_stats(
                spec["id"], spec["category"], spec["name"], spec["symbol"], spec["note"]
            )
            assets.append(stats)
            monthly_series_by_id[spec["id"]] = monthly_ret_map
            print(f"OK  {spec['id']:24s} {spec['symbol']}")
        except Exception as exc:
            errors.append({"id": spec["id"], "symbol": spec["symbol"], "error": str(exc)})
            print(f"ERR {spec['id']:24s} {spec['symbol']}: {exc}")

    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    for key, payload in curated.items():
        if key.startswith("_"):
            continue
        if args.only and key not in args.only:
            continue
        assets.append(build_curated_asset(key, payload))

    # 相关性矩阵：月度（仅限可自动抓取月频数据的ETF/指数代理，窗口与月度波动率一致）
    # 及年度（覆盖全部资产，含对冲基金/私募股权真实指数，用各自已展示的年度收益序列）
    monthly_corr = correlation_matrix(monthly_series_by_id, MIN_MONTHLY_OVERLAP)
    annual_series_by_id = {
        a["id"]: {k: v for k, v in a["annualReturnsPct"].items()} for a in assets if a.get("annualReturnsPct")
    }
    annual_corr = correlation_matrix(annual_series_by_id, MIN_ANNUAL_OVERLAP)

    generated_at = datetime.now(timezone.utc).isoformat()
    payload_out = {
        "version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "generatedAt": generated_at,
        "methodology": {
            "summary": "每类资产选取一个流动性最好、历史最长的公开上市代理标的（股票ETF/指数、债券ETF、商品期货连续合约等），"
                        "用其调整后收盘价计算日历年度总回报、以及年度/月度/日度三种频率的年化波动率。"
                        "对冲基金与私募股权不存在可免费程序化抓取的真实基金净值序列，这两类改为人工检索并标注来源的真实指数"
                        "（HFRI对冲基金等权复合指数、Cambridge Associates美国私募股权指数），同时保留对应的上市ETF代理作为流动性参考。",
            "annualWindow": f"最近{MAX_ANNUAL_YEARS}个完整日历年度（不足{MAX_ANNUAL_YEARS}年的标的以实际可得年数为准，已在各条目dataStartYear中注明）",
            "monthlyVolWindow": f"最近{MONTHLY_VOL_YEARS}年月度收益率的标准差，乘以√12年化",
            "dailyVolWindow": f"最近{DAILY_VOL_YEARS}年日收益率的标准差，乘以√252年化",
            "caveats": [
                "股票类指数（标普500/欧洲斯托克50/日经225）为价格指数，未计入股息再投资，实际总回报会更高；全球股票(ACWI)与跨资产另类类别(PSP/QAI)为含息ETF总回报。",
                "私募股权与对冲基金的『上市代理』(PSP/QAI)与其『真实指数』(Cambridge Associates/HFRI)收益特征差异很大，不可互相替代，请分别参考。",
                "比特币、全球股票ETF、多数商品/另类ETF的历史均不足30年，已在各自dataStartYear/yearsOfAnnualData字段中如实标注，不做任何方式的历史数据外推或编造。",
                f"相关性矩阵分两套：『月度』用最近{MONTHLY_VOL_YEARS}年月度收益率计算，仅覆盖有逐月行情的13个ETF/指数代理（对冲基金与私募股权的真实指数无月度数据，不参与此表）；"
                f"『年度』用各资产展示的年度收益序列计算，覆盖全部15个资产（含HFRI/Cambridge真实指数），但年度数据点少、相关性估计噪音更大。"
                f"两套矩阵均要求至少{MIN_MONTHLY_OVERLAP}个重叠月份/{MIN_ANNUAL_OVERLAP}个重叠年份才计算相关系数，样本不足的资产对将相关系数标为null并保留实际重叠样本量(n)，不做估算填充。",
                "相关系数为Pearson线性相关，基于各标的本币（美股/欧股/日股/原始计价货币）收益率计算，未做汇率换算；日经225等非美元计价资产与美元资产的相关系数因此同时包含了市场联动和汇率波动两部分影响，解读时需注意。",
                "年度相关性矩阵中部分资产对（尤其含对冲基金/私募股权真实指数、比特币、现金等历史较短或数据有缺口的资产）重叠样本量(n)很小（个位数到十几年），相关系数噪音大、稳健性低，使用前请参考n值；月度相关性矩阵样本量更大（通常100+个月），统计稳健性更高，是更适合做资产配置参考的主表。",
            ],
        },
        "assets": assets,
        "correlations": {
            "monthly": monthly_corr | {
                "windowYears": MONTHLY_VOL_YEARS,
                "minOverlap": MIN_MONTHLY_OVERLAP,
                "description": f"最近{MONTHLY_VOL_YEARS}年月度收益率相关系数（Pearson），仅限13个可自动抓取月频数据的ETF/指数代理",
            },
            "annual": annual_corr | {
                "windowYears": MAX_ANNUAL_YEARS,
                "minOverlap": MIN_ANNUAL_OVERLAP,
                "description": f"各资产展示的年度收益序列（最多{MAX_ANNUAL_YEARS}年）相关系数（Pearson），覆盖全部资产含对冲基金/私募股权真实指数",
            },
        },
        "errors": errors,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload_out, ensure_ascii=False, indent=None, separators=(",", ":")), encoding="utf-8")

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = {"snapshots": []}
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            history = {"snapshots": []}
    history.setdefault("snapshots", []).append({
        "date": datetime.now(timezone.utc).date().isoformat(),
        "generatedAt": generated_at,
        "assetCount": len(assets),
        "errorCount": len(errors),
    })
    history["snapshots"] = history["snapshots"][-400:]
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nOK: {len(assets)} 个资产类别 -> {OUTPUT_PATH}  ({len(errors)} 个失败)")


if __name__ == "__main__":
    main()
