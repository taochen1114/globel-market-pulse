"""Fetch global market data and store it as structured JSON."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd
import yfinance as yf

from utils import sync_output, today_iso

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


@dataclass
class TickerSpec:
    symbol: str
    label: str
    field_map: Optional[Dict[str, str]] = None


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


def fetch_equity_markets() -> Dict[str, Dict[str, Optional[float]]]:
    specs = [
        TickerSpec(symbol="^TWII", label="TWSE Weighted Index"),
        TickerSpec(symbol="^GSPC", label="S&P 500"),
        TickerSpec(symbol="^IXIC", label="NASDAQ Composite"),
        TickerSpec(symbol="^DJI", label="Dow Jones Industrial"),
        TickerSpec(symbol="^HSI", label="Hang Seng Index"),
        TickerSpec(symbol="^N225", label="Nikkei 225"),
        TickerSpec(symbol="^STOXX", label="STOXX Europe 600"),
        TickerSpec(symbol="^FTSE", label="FTSE 100"),
    ]
    result: Dict[str, Dict[str, Optional[float]]] = {}

    for spec in specs:
        ticker = yf.Ticker(spec.symbol)
        close_price = latest_close(ticker)
        change_pct = daily_change_percent(ticker)
        volume = None
        try:
            history = ticker.history(period="5d", interval="1d")
            if not history.empty:
                volume = float(history["Volume"].dropna().iloc[-1])
        except Exception as exc:  # noqa: BLE001 - log and continue
            LOGGER.warning("Unable to fetch volume for %s: %s", spec.symbol, exc)

        result[spec.symbol] = {
            "name": spec.label,
            "close": close_price,
            "daily_change_pct": change_pct,
            "volume": volume,
        }

    return result


def fetch_forex() -> Dict[str, Optional[float]]:
    tickers = {
        "USD/TWD": "TWD=X",
        "EUR/USD": "EURUSD=X",
        "JPY/USD": "JPY=X",
    }
    forex: Dict[str, Optional[float]] = {}
    for label, symbol in tickers.items():
        ticker = yf.Ticker(symbol)
        forex[label] = latest_close(ticker)
    return forex


def fetch_commodities() -> Dict[str, Optional[float]]:
    tickers = {
        "Gold": "GC=F",
        "Oil": "CL=F",
        "Copper": "HG=F",
    }
    commodities: Dict[str, Optional[float]] = {}
    for label, symbol in tickers.items():
        ticker = yf.Ticker(symbol)
        commodities[label] = latest_close(ticker)
    return commodities


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
        "2Y": ["^UST2Y", "^US2Y"],
        "10Y": ["^TNX", "^US10Y"],
    }
    rates: Dict[str, Optional[float]] = {}
    for label, symbols in candidates.items():
        value, symbol = _first_available_close(symbols)
        if value is not None and label == "10Y" and symbol == "^TNX":
            # Yahoo Finance stores the 10Y yield as percentage * 10 for ^TNX.
            value = round(value / 10, 4)
        rates[label] = value
    return rates


def fetch_sentiment() -> Dict[str, Optional[float]]:
    ticker = yf.Ticker("^VIX")
    return {"VIX": latest_close(ticker)}


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
        history = ticker.history(period="5d", interval="1d")
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


def build_payload() -> Dict[str, object]:
    return {
        "date": today_iso(),
        "markets": fetch_equity_markets(),
        "forex": fetch_forex(),
        "commodities": fetch_commodities(),
        "rates": fetch_rates(),
        "sentiment": fetch_sentiment(),
        "funds": fetch_etf_flows(),
    }


def main() -> None:
    LOGGER.info("Fetching global market data...")
    payload = build_payload()
    LOGGER.info("Persisting market data snapshot")
    sync_output("market_data.json", payload)
    LOGGER.info("Market data updated")


if __name__ == "__main__":
    main()
