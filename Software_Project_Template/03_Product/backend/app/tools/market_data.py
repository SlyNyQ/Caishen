from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
from typing import Any, Protocol

import pandas as pd


TICKER_RE = re.compile(r"(?<![A-Za-z0-9])\$?([A-Z]{1,6}(?:[.-][A-Z]{1,4})?)(?![A-Za-z0-9])")
TICKER_STOPWORDS = {
    "AI",
    "A",
    "AN",
    "AND",
    "ARE",
    "BUY",
    "CAISHEN",
    "COMPARE",
    "ETF",
    "FOR",
    "HOW",
    "I",
    "IS",
    "LONG",
    "OR",
    "RISK",
    "SELL",
    "SHORT",
    "STOCK",
    "THE",
    "THIS",
    "TO",
    "WHAT",
    "WITH",
}


class MarketDataUnavailable(RuntimeError):
    pass


class MarketDataClient(Protocol):
    def get_snapshot(self, ticker: str) -> dict[str, Any]:
        ...


def extract_tickers(message: str, explicit_tickers: list[str] | None = None) -> list[str]:
    tickers = [ticker.strip().upper().lstrip("$") for ticker in explicit_tickers or []]
    for match in TICKER_RE.finditer(message):
        ticker = match.group(1).upper()
        if ticker not in TICKER_STOPWORDS:
            tickers.append(ticker)
    return list(dict.fromkeys(ticker for ticker in tickers if ticker))[:8]


def _safe_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) or math.isinf(number) else round(number, 4)


def _period_return(closes: pd.Series, trading_days: int) -> float | None:
    if len(closes) < 2:
        return None
    start_index = max(0, len(closes) - trading_days - 1)
    start = _safe_float(closes.iloc[start_index])
    end = _safe_float(closes.iloc[-1])
    if start in (None, 0) or end is None:
        return None
    return round(((end / start) - 1) * 100, 2)


def build_market_snapshot(
    ticker: str,
    *,
    history: pd.DataFrame,
    info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    info = info or {}
    if history.empty or "Close" not in history:
        raise MarketDataUnavailable(f"No market history is available for {ticker}.")
    closes = history["Close"].dropna()
    if closes.empty:
        raise MarketDataUnavailable(f"No closing-price history is available for {ticker}.")

    current_price = _safe_float(closes.iloc[-1])
    previous_close = _safe_float(closes.iloc[-2]) if len(closes) > 1 else None
    percent_change = None
    if current_price is not None and previous_close not in (None, 0):
        percent_change = round(((current_price / previous_close) - 1) * 100, 2)

    daily_returns = closes.pct_change().dropna()
    volatility = None
    if not daily_returns.empty:
        volatility = round(float(daily_returns.std()) * math.sqrt(252) * 100, 2)

    last_index = closes.index[-1]
    data_as_of = (
        last_index.isoformat()
        if hasattr(last_index, "isoformat")
        else datetime.now(timezone.utc).isoformat()
    )
    return {
        "ticker": ticker.upper(),
        "company_name": str(info.get("longName") or info.get("shortName") or ticker.upper()),
        "currency": info.get("currency"),
        "current_price": current_price,
        "previous_close": previous_close,
        "percent_change": percent_change,
        "performance_1m": _period_return(closes, 21),
        "performance_3m": _period_return(closes, 63),
        "performance_1y": _period_return(closes, 252),
        "annualized_volatility": volatility,
        "market_cap": _safe_float(info.get("marketCap")),
        "pe_ratio": _safe_float(info.get("trailingPE")),
        "data_as_of": data_as_of,
        "status": "available",
        "note": "Market data may be delayed and should be independently verified.",
    }


@dataclass(slots=True)
class YFinanceMarketDataClient:
    history_period: str = "1y"

    def get_snapshot(self, ticker: str) -> dict[str, Any]:
        try:
            import yfinance as yf

            instrument = yf.Ticker(ticker)
            history = instrument.history(period=self.history_period, interval="1d", auto_adjust=False)
            return build_market_snapshot(ticker, history=history, info=instrument.info or {})
        except MarketDataUnavailable:
            raise
        except Exception as exc:
            raise MarketDataUnavailable(f"Live market data for {ticker} is unavailable: {exc}") from exc


def unavailable_snapshot(ticker: str, detail: str) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "company_name": ticker.upper(),
        "status": "unavailable",
        "note": detail,
    }
