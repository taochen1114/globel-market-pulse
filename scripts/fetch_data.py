"""Fetch global market data and store it as structured JSON."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yfinance as yf

from utils import DATA_DIR, sync_history, sync_output, today_iso
# --- auto skip logic: weekend / no market day ---

import datetime
import sys

# Taiwan timezone (UTC+8)
tw_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)

# Monday = 0, Tue=1 ... Sat=5, Sun=6
if tw_now.weekday() >= 5:
    print(f"[SKIP] Weekend {tw_now.strftime('%Y-%m-%d %H:%M:%S')} (TW) → market closed, skip workflow.")
    sys.exit(78)   # ← neutral exit, stops the rest of GitHub Actions steps

# global holidays skip
HOLIDAYS = {
    "2025-12-25",
    "2026-01-01",
}

today_str = tw_now.strftime("%Y-%m-%d")

if today_str in HOLIDAYS:
    print(f"[SKIP] Global holiday ({today_str}) → skip workflow.")
    sys.exit(78)
    
# --- end skip logic ---

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

PERFORMANCE_OFFSETS = {
    "1m": pd.DateOffset(months=1),
    "2m": pd.DateOffset(months=2),
    "3m": pd.DateOffset(months=3),
    "6m": pd.DateOffset(months=6),
    "1y": pd.DateOffset(years=1),
    "3y": pd.DateOffset(years=3),
    "5y": pd.DateOffset(years=5),
}

PERFORMANCE_LABELS = {
    "1m": "近1個月",
    "2m": "近2個月",
    "3m": "近3個月",
    "6m": "近6個月",
    "1y": "近1年",
    "3y": "近3年",
    "5y": "近5年",
}


@dataclass
class AssetSpec:
    symbol: str
    name: str
    category: str
    slug: Optional[str] = None
    region: Optional[str] = None


@dataclass
class ForexSpec:
    symbol: str
    name: str
    pair: str
    category: str = "forex"


def slugify_symbol(symbol: str) -> str:
    """Convert ticker symbols to filesystem-friendly slugs."""

    slug = "".join(char.lower() if char.isalnum() else "-" for char in symbol)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "asset"


def history_path(category: str, slug: str) -> Path:
    return DATA_DIR / "history" / category / f"{slug}.json"


def load_history(category: str, slug: str) -> List[Dict[str, Optional[float]]]:
    path = history_path(category, slug)
    if not path.exists():
        return []
    try:
        return pd.read_json(path).to_dict(orient="records")  # type: ignore[return-value]
    except ValueError:
        return []


def persist_history(category: str, slug: str, entries: List[Dict[str, Optional[float]]]) -> None:
    relative = f"history/{category}/{slug}.json"
    sync_history(relative, entries)


def update_history(
    category: str,
    slug: str,
    entry: Dict[str, Optional[float]],
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]],
) -> List[Dict[str, Optional[float]]]:
    history = registry.setdefault(category, {}).get(slug)
    if history is None:
        history = load_history(category, slug)
    if history and history[-1].get("date") == entry.get("date"):
        history[-1] = entry
    else:
        history.append(entry)
    persist_history(category, slug, history)
    registry[category][slug] = history
    return history


def latest_close(ticker: yf.Ticker) -> Optional[float]:
    """Return the most recent close price for a ticker."""
    history = ticker.history(period="5d", interval="1d")
    if history.empty:
        return None
    return float(history["Close"].dropna().iloc[-1])


def daily_change_percent(ticker: yf.Ticker) -> Optional[float]:
    """Return the most recent daily percentage change."""
    history = ticker.history(period="5d", interval="1d")
    if history.empty or len(history) < 2:
        return None
    latest = history["Close"].dropna().iloc[-1]
    previous = history["Close"].dropna().iloc[-2]
    if previous == 0:
        return None
    return float((latest - previous) / previous * 100)


MARKET_SPECS: List[AssetSpec] = [
    AssetSpec(symbol="^GSPC", name="S&P 500", category="markets", slug="gspc", region="美國"),
    AssetSpec(symbol="^DJI", name="Dow Jones Industrial", category="markets", slug="dji", region="美國"),
    AssetSpec(symbol="^IXIC", name="NASDAQ Composite", category="markets", slug="ixic", region="美國"),
    AssetSpec(symbol="^TWII", name="TWSE Weighted Index", category="markets", slug="twii", region="台灣"),
    AssetSpec(symbol="^HSI", name="Hang Seng Index", category="markets", slug="hsi", region="香港"),
    AssetSpec(symbol="^N225", name="Nikkei 225", category="markets", slug="n225", region="日本"),
    AssetSpec(symbol="^STOXX", name="STOXX Europe 600", category="markets", slug="stoxx", region="歐洲"),
    AssetSpec(symbol="^FTSE", name="FTSE 100", category="markets", slug="ftse", region="英國"),
]


def fetch_asset_series(
    specs: Iterable[AssetSpec],
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]],
    *,
    include_performance: bool = False,
    include_volume: bool = False,
) -> List[Dict[str, object]]:
    today = today_iso()
    series: List[Dict[str, object]] = []

    for spec in specs:
        ticker = yf.Ticker(spec.symbol)
        try:
            close_price = latest_close(ticker)
        except Exception as exc:  # noqa: BLE001 - log and continue with empty data
            LOGGER.warning("Unable to fetch latest close for %s: %s", spec.symbol, exc)
            close_price = None

        try:
            change_pct = daily_change_percent(ticker)
        except Exception as exc:  # noqa: BLE001 - log and continue with empty data
            LOGGER.warning("Unable to compute daily change for %s: %s", spec.symbol, exc)
            change_pct = None

        volume: Optional[float] = None
        if include_volume:
            try:
                history = ticker.history(period="5d", interval="1d")
                if not history.empty:
                    volume = float(history["Volume"].dropna().iloc[-1])
            except Exception as exc:  # noqa: BLE001 - log and continue
                LOGGER.warning("Unable to fetch volume for %s: %s", spec.symbol, exc)

        performance: Optional[Dict[str, Optional[float]]] = None
        if include_performance:
            performance = historical_performance(ticker)

        slug = spec.slug or slugify_symbol(spec.symbol)
        update_history(
            spec.category,
            slug,
            {"date": today, "close": close_price, "change_pct": change_pct},
            registry,
        )

        record: Dict[str, object] = {
            "symbol": spec.symbol,
            "name": spec.name,
            "close": close_price,
            "daily_change_pct": change_pct,
            "history": f"{spec.category}/{slug}",
        }
        if spec.region:
            record["region"] = spec.region
        if include_volume:
            record["volume"] = volume
        if include_performance and performance is not None:
            record["performance"] = performance

        series.append(record)

    return series


def fetch_equity_markets(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> List[Dict[str, object]]:
    return fetch_asset_series(
        MARKET_SPECS,
        registry,
        include_performance=True,
        include_volume=True,
    )


def _first_valid_close(history: pd.DataFrame, threshold: pd.Timestamp) -> Optional[float]:
    """Return the earliest available close price after the threshold date."""

    if history.empty or "Close" not in history:
        return None

    filtered = history.loc[history.index >= threshold]
    if filtered.empty:
        return None

    close_series = filtered["Close"].dropna()
    if close_series.empty:
        return None

    return float(close_series.iloc[0])


def historical_performance(ticker: yf.Ticker) -> Dict[str, Optional[float]]:
    """Compute multi-period percentage changes for the provided ticker."""

    try:
        history = ticker.history(period="5y", interval="1d")
    except Exception as exc:  # noqa: BLE001 - failure should not break pipeline
        LOGGER.warning("Unable to fetch historical data for %s: %s", ticker.ticker, exc)
        return {period: None for period in PERFORMANCE_OFFSETS}

    if history.empty or "Close" not in history:
        return {period: None for period in PERFORMANCE_OFFSETS}

    close_series = history["Close"].dropna()
    if close_series.empty:
        return {period: None for period in PERFORMANCE_OFFSETS}

    latest_close = float(close_series.iloc[-1])
    latest_date = close_series.index[-1]

    performance: Dict[str, Optional[float]] = {}
    for period, offset in PERFORMANCE_OFFSETS.items():
        threshold_date = latest_date - offset
        starting_close = _first_valid_close(history, threshold_date)

        if starting_close is None or starting_close == 0:
            performance[period] = None
            continue

        change = (latest_close - starting_close) / starting_close * 100
        performance[period] = float(change)

    return performance


FOREX_SPECS: List[ForexSpec] = [
    ForexSpec(symbol="DX-Y.NYB", name="美元指數", pair="DXY"),
    ForexSpec(symbol="TWD=X", name="美元/台幣", pair="USD/TWD"),
    ForexSpec(symbol="EURUSD=X", name="歐元/美元", pair="EUR/USD"),
    ForexSpec(symbol="GBPUSD=X", name="英鎊/美元", pair="GBP/USD"),
    ForexSpec(symbol="JPY=X", name="美元/日圓", pair="USD/JPY"),
    ForexSpec(symbol="KRW=X", name="美元/韓圓", pair="USD/KRW"),
    ForexSpec(symbol="HKD=X", name="美元/港幣", pair="USD/HKD"),
    ForexSpec(symbol="CNY=X", name="美元/人民幣", pair="USD/CNY"),
]


def fetch_forex(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []

    today = today_iso()
    for spec in FOREX_SPECS:
        ticker = yf.Ticker(spec.symbol)
        try:
            close_price = latest_close(ticker)
        except Exception as exc:  # noqa: BLE001 - log and continue
            LOGGER.warning("Unable to fetch forex rate for %s: %s", spec.symbol, exc)
            close_price = None

        try:
            change_pct = daily_change_percent(ticker)
        except Exception as exc:  # noqa: BLE001 - log and continue
            LOGGER.warning("Unable to compute forex change for %s: %s", spec.symbol, exc)
            change_pct = None

        slug = slugify_symbol(spec.pair)
        update_history(
            spec.category,
            slug,
            {"date": today, "close": close_price, "change_pct": change_pct},
            registry,
        )

        results.append(
            {
                "symbol": spec.symbol,
                "name": spec.name,
                "pair": spec.pair,
                "close": close_price,
                "daily_change_pct": change_pct,
                "history": f"{spec.category}/{slug}",
            }
        )

    return results


COMMODITY_SPECS: List[AssetSpec] = [
    AssetSpec(symbol="GC=F", name="COMEX 黃金", category="commodities", slug="gold"),
    AssetSpec(symbol="CL=F", name="NYMEX 原油", category="commodities", slug="wti"),
    AssetSpec(symbol="HG=F", name="COMEX 銅", category="commodities", slug="copper"),
]

MACRO_SPECS: List[AssetSpec] = [
    AssetSpec(symbol="DX-Y.NYB", name="美元指數 (DXY)", category="macro", slug="dxy"),
]

US_TECH_SPECS: List[AssetSpec] = [
    AssetSpec(symbol="AAPL", name="Apple", category="us_tech", slug="apple"),
    AssetSpec(symbol="GOOGL", name="Google", category="us_tech", slug="google"),
    AssetSpec(symbol="AMZN", name="Amazon", category="us_tech", slug="amazon"),
    AssetSpec(symbol="MSFT", name="Microsoft", category="us_tech", slug="microsoft"),
    AssetSpec(symbol="META", name="Meta", category="us_tech", slug="meta"),
    AssetSpec(symbol="NVDA", name="NVIDIA", category="us_tech", slug="nvidia"),
    AssetSpec(symbol="AMD", name="AMD", category="us_tech", slug="amd"),
    AssetSpec(symbol="INTC", name="Intel", category="us_tech", slug="intel"),
    AssetSpec(symbol="TSLA", name="Tesla", category="us_tech", slug="tesla"),
]

CRYPTO_SPECS: List[AssetSpec] = [
    AssetSpec(symbol="BTC-USD", name="Bitcoin", category="crypto", slug="bitcoin"),
    AssetSpec(symbol="ETH-USD", name="Ethereum", category="crypto", slug="ethereum"),
    AssetSpec(symbol="USDT-USD", name="Tether (USDT)", category="crypto", slug="tether"),
]


def fetch_commodities(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> List[Dict[str, object]]:
    return fetch_asset_series(COMMODITY_SPECS, registry)


def fetch_macro_assets(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> List[Dict[str, object]]:
    return fetch_asset_series(MACRO_SPECS, registry)


def fetch_us_tech(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> List[Dict[str, object]]:
    return fetch_asset_series(US_TECH_SPECS, registry, include_volume=True)


def fetch_crypto_assets(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> List[Dict[str, object]]:
    return fetch_asset_series(CRYPTO_SPECS, registry)


def _first_available_close(symbols: list[str]) -> tuple[Optional[float], Optional[str]]:
    """Return the first non-null close price and symbol from the candidates."""

    for candidate in symbols:
        ticker = yf.Ticker(candidate)
        try:
            value = latest_close(ticker)
        except Exception as exc:  # noqa: BLE001 - log and try next
            LOGGER.warning("Failed to fetch rate for %s: %s", candidate, exc)
            continue

        if value is not None:
            return value, candidate

    return None, None


def fetch_rates() -> Dict[str, Optional[float]]:
    candidates = {
        # Yahoo's ^IRX quotes the 13-week T-bill rate (scaled by 10); used as a stable
        # proxy for the front end to avoid delisted 2Y tickers.
        "2Y": ["^IRX", "ZT=F"],
        # ^TNX is the most reliable 10Y yield ticker; keep other options as fallback.
        "10Y": ["^TNX", "^US10Y", "TMUBMUSD10Y"],
    }

    # Some Yahoo Finance rate tickers are quoted as percentage * 10 (e.g., ^TNX, ^IRX).
    # Normalize these to human-readable percentages.
    scale_by_ten = {"^TNX", "^IRX"}

    rates: Dict[str, Optional[float]] = {}
    for label, symbols in candidates.items():
        value, symbol = _first_available_close(symbols)
        if value is not None and symbol in scale_by_ten:
            value = round(value / 10, 4)
        rates[label] = value
    return rates


def fetch_sentiment() -> Dict[str, Optional[float]]:
    ticker = yf.Ticker("^VIX")
    try:
        return {"VIX": latest_close(ticker)}
    except Exception as exc:  # noqa: BLE001 - log and continue
        LOGGER.warning("Unable to fetch sentiment index: %s", exc)
        return {"VIX": None}


def fetch_etf_flows() -> Dict[str, Dict[str, Optional[float]]]:
    etfs = {
        "QQQ": "Invesco QQQ",
        "SPY": "SPDR S&P 500",
        "EWT": "iShares MSCI Taiwan",
        "EFA": "iShares MSCI EAFE",
    }
    flows: Dict[str, Dict[str, Optional[float]]] = {}
    for symbol, name in etfs.items():
        ticker = yf.Ticker(symbol)
        try:
            history = ticker.history(period="5d", interval="1d")
        except Exception as exc:  # noqa: BLE001 - optional data
            LOGGER.warning("Unable to fetch ETF history for %s: %s", symbol, exc)
            history = pd.DataFrame()
        if history.empty:
            flows[symbol] = {"name": name, "net_flow_estimate": None, "volume": None}
            continue
        latest_volume = float(history["Volume"].dropna().iloc[-1]) if not history["Volume"].dropna().empty else None
        # Use change in assets under management as a proxy if available.
        aum = None
        try:
            holdings = ticker.funds
            if isinstance(holdings, pd.DataFrame) and not holdings.empty and "Net Assets" in holdings.columns:
                aum = float(holdings["Net Assets"].dropna().iloc[0])
        except Exception:  # noqa: BLE001 - optional data
            aum = None
        flows[symbol] = {
            "name": name,
            "net_flow_estimate": aum,
            "volume": latest_volume,
        }
    return flows


def build_highlights(
    macro_assets: List[Dict[str, object]],
    commodities: List[Dict[str, object]],
    markets: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    selections = [
        ("macro", "DX-Y.NYB", "美元"),
        ("commodities", "GC=F", "黃金"),
        ("commodities", "CL=F", "原油"),
        ("markets", "^GSPC", "美國"),
        ("markets", "^TWII", "台灣"),
        ("markets", "^HSI", "香港"),
        ("markets", "^N225", "日本"),
        ("markets", "^STOXX", "歐洲"),
    ]

    sources = {
        "macro": macro_assets,
        "commodities": commodities,
        "markets": markets,
    }

    highlights: List[Dict[str, object]] = []
    for category, symbol, label in selections:
        dataset = sources.get(category, [])
        match = next((item for item in dataset if item.get("symbol") == symbol), None)
        if not match:
            continue
        entry = dict(match)
        entry["label"] = label
        highlights.append(entry)

    return highlights


def persist_history_indexes(
    registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]]
) -> None:
    for category, series in registry.items():
        aggregate = {slug: entries for slug, entries in series.items()}
        sync_history(f"history/{category}.json", aggregate)


def build_payload() -> Dict[str, object]:
    history_registry: Dict[str, Dict[str, List[Dict[str, Optional[float]]]]] = {}

    markets = fetch_equity_markets(history_registry)
    forex = fetch_forex(history_registry)
    commodities = fetch_commodities(history_registry)
    macro = fetch_macro_assets(history_registry)
    us_tech = fetch_us_tech(history_registry)
    crypto = fetch_crypto_assets(history_registry)

    highlights = build_highlights(macro, commodities, markets)

    persist_history_indexes(history_registry)

    return {
        "date": today_iso(),
        "highlights": highlights,
        "macro": macro,
        "markets": markets,
        "forex": forex,
        "commodities": commodities,
        "us_tech": us_tech,
        "crypto": crypto,
        "rates": fetch_rates(),
        "sentiment": fetch_sentiment(),
        "funds": fetch_etf_flows(),
        "performance_periods": PERFORMANCE_LABELS,
    }


def main() -> None:
    LOGGER.info("Fetching global market data...")
    payload = build_payload()
    LOGGER.info("Persisting market data snapshot")
    sync_output("market_data.json", payload)
    LOGGER.info("Market data updated")


if __name__ == "__main__":
    main()
