"""
Data fetching module for Indian stock market (NSE/BSE) using yfinance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Optional, Union

# Indian indices (Yahoo Finance symbols) – use as-is, no .NS suffix
# NSE stocks get .NS appended unless ticker already has .NS, .BO, or ^
NSE_INDEX_PREFIX = "^"
EXCHANGE_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}


def _normalize_ticker(ticker: str) -> str:
    """
    Normalize ticker for yfinance.
    - Indices (e.g. ^NSEI, ^BSESN): return as-is.
    - Already suffixed (e.g. RELIANCE.NS, RELIANCE.BO): return as-is.
    - Plain symbol (e.g. RELIANCE, TCS): append .NS for NSE.
    """
    s = ticker.strip().upper()
    if s.startswith(NSE_INDEX_PREFIX) or s.endswith((".NS", ".BO")):
        return s
    return f"{s}.NS"


def fetch_stock_data(
    ticker: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data using yfinance.

    Args:
        ticker: Symbol (e.g. RELIANCE, TCS, ^NSEI, ^BSESN). NSE stocks get .NS appended.
        start_date: Start date (string 'YYYY-MM-DD' or datetime).
        end_date: End date (string 'YYYY-MM-DD' or datetime).

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume; or None if
        ticker is invalid or data is unavailable.
    """
    if not ticker or not isinstance(ticker, str):
        return None
    yf_symbol = _normalize_ticker(ticker)
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        if start >= end:
            return None
    except Exception:
        return None

    try:
        # yfinance sometimes needs end date to be exclusive (add 1 day)
        # Also ensure we're using date-only (no time component)
        start_ts = pd.Timestamp(start).normalize()
        end_ts = pd.Timestamp(end).normalize() + pd.Timedelta(days=1)
        
        data = yf.download(
            yf_symbol,
            start=start_ts,
            end=end_ts,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if data is None or data.empty:
            return None
        # yf.download can return MultiIndex columns if multiple tickers; we pass one
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        required = ["Open", "High", "Low", "Close"]
        if not all(c in data.columns for c in required):
            return None
        out = data[required].copy()
        if "Volume" in data.columns:
            out["Volume"] = data["Volume"].values
        else:
            out["Volume"] = 0
        return out.astype(float)
    except Exception as e:
        # Log the error for debugging (can be removed in production)
        print(f"Error fetching data for {yf_symbol}: {str(e)}")
        return None


def get_yahoo_symbol(symbol: str, exchange: str = "NSE") -> str:
    """
    Convert Indian stock symbol to Yahoo Finance format.
    E.g., RELIANCE + NSE -> RELIANCE.NS. Used by get_stock_info and legacy callers.
    """
    suffix = EXCHANGE_SUFFIX.get(exchange.upper(), ".NS")
    clean = symbol.strip().upper()
    if clean.startswith(NSE_INDEX_PREFIX) or clean.endswith((".NS", ".BO")):
        return clean
    return f"{clean}{suffix}"


def get_stock_info(symbol: str, exchange: str = "NSE") -> Optional[dict]:
    """
    Get basic info for an Indian stock (name, sector, etc.) if available.
    """
    ticker = get_yahoo_symbol(symbol, exchange)
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "shortName": info.get("shortName", symbol),
            "longName": info.get("longName", symbol),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
        }
    except Exception:
        return None
