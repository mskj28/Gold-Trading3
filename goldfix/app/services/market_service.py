from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yfinance as yf

from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_PRICE_COLUMNS = ("Open", "High", "Low", "Close")


def candidate_symbols(symbol: str) -> list[str]:
    normalized = symbol.upper().strip()
    if normalized in {"XAUUSD", "XAUUSD=X", "GOLD"}:
        # Try spot gold first, then COMEX futures, then the GLD ETF as a last-resort proxy.
        return ["XAUUSD=X", "GC=F", "GLD"]
    return [symbol]


def request_variants(period: str, interval: str) -> list[tuple[str, str]]:
    variants: list[tuple[str, str]] = [(period, interval)]

    if interval != "1d":
        variants.append((period, "1d"))
    if period != "1mo":
        variants.append(("1mo", interval))

    variants.append(("6mo", "1d"))

    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in variants:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        flattened = []
        for col in df.columns:
            values = [str(part) for part in col if part not in (None, "")]
            flattened.append(values[0] if values else "")
        df.columns = flattened
    return df


def _normalize_market_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = _flatten_columns(df.copy()).reset_index()

    if "Datetime" in df.columns:
        df.rename(columns={"Datetime": "timestamp"}, inplace=True)
    elif "Date" in df.columns:
        df.rename(columns={"Date": "timestamp"}, inplace=True)

    missing = [col for col in REQUIRED_PRICE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required market columns: {missing}")

    for col in REQUIRED_PRICE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=list(REQUIRED_PRICE_COLUMNS)).reset_index(drop=True)
    return df


def _download_variants(ticker: str, period: str, interval: str) -> Iterable[pd.DataFrame]:
    download_attempts = [
        {"tickers": ticker, "period": period, "interval": interval, "progress": False, "auto_adjust": False, "threads": False},
    ]

    for kwargs in download_attempts:
        try:
            logger.info(f"Fetching market data with yf.download: {kwargs}")
            yield yf.download(**kwargs)
        except Exception as exc:
            logger.warning(f"yf.download failed for {ticker}: {exc}")

    try:
        logger.info(f"Fetching market data with yf.Ticker.history: ticker={ticker}")
        history = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        yield history
    except Exception as exc:
        logger.warning(f"yf.Ticker.history failed for {ticker}: {exc}")


def _load_local_fallback_frame() -> pd.DataFrame:
    csv_path = Path(__file__).resolve().parents[1] / "backtest" / "data.csv"
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        logger.warning("Local fallback CSV could not be read from %s: %s", csv_path, exc)
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    rename_map = {
        "close": "Close",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "volume": "Volume",
    }
    df = df.rename(columns=rename_map)

    if "Close" not in df.columns:
        return pd.DataFrame()

    if "Open" not in df.columns:
        df["Open"] = df["Close"].shift(1).fillna(df["Close"])
    if "High" not in df.columns:
        df["High"] = df[["Open", "Close"]].max(axis=1) + 1.0
    if "Low" not in df.columns:
        df["Low"] = df[["Open", "Close"]].min(axis=1) - 1.0
    if "Volume" not in df.columns:
        df["Volume"] = 0.0
    if "timestamp" not in df.columns:
        df.insert(0, "timestamp", pd.date_range(end=pd.Timestamp.utcnow().floor("D"), periods=len(df), freq="B"))

    return _normalize_market_frame(df)


def _build_synthetic_market_frame(symbol: str, period: str, interval: str) -> pd.DataFrame:
    period_days = {
        "1d": 1,
        "5d": 5,
        "7d": 7,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "max": 730,
    }
    days = period_days.get(period, 180)

    if interval.endswith("h"):
        step = max(int(interval[:-1] or "1"), 1)
        rows = max(80, int((days * 24) / step))
        freq = f"{step}h"
    else:
        step = max(int(interval[:-1] or "1"), 1) if interval.endswith("d") else 1
        rows = max(80, int(days / step))
        freq = "B" if step == 1 else f"{step}B"

    end = pd.Timestamp.utcnow().floor("h" if interval.endswith("h") else "D")
    timestamps = pd.date_range(end=end, periods=rows, freq=freq)

    normalized = symbol.upper().strip()
    base_price = 2325.0 if normalized in {"XAUUSD", "XAUUSD=X", "GC=F", "GOLD"} else 220.0

    trend = np.linspace(-18.0, 22.0, rows)
    cycle_fast = 4.0 * np.sin(np.linspace(0, 10 * np.pi, rows))
    cycle_slow = 11.0 * np.sin(np.linspace(0, 2.5 * np.pi, rows))
    close = base_price + trend + cycle_fast + cycle_slow
    open_price = np.concatenate(([close[0] - 0.8], close[:-1]))
    high = np.maximum(open_price, close) + 1.2 + np.abs(np.sin(np.linspace(0, 5 * np.pi, rows)))
    low = np.minimum(open_price, close) - 1.2 - np.abs(np.cos(np.linspace(0, 5 * np.pi, rows)))
    volume = np.linspace(1200, 2200, rows)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "Open": open_price,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        }
    )
    df["fallback_source"] = "synthetic_offline"
    return df.reset_index(drop=True)


def _build_fallback_market_frame(symbol: str, period: str, interval: str) -> pd.DataFrame:
    local_df = _load_local_fallback_frame()
    if not local_df.empty:
        logger.warning("Using local CSV fallback market data because live Yahoo Finance data is unavailable.")
        local_df["fallback_source"] = "local_csv"
        return local_df

    logger.warning("Using synthetic fallback market data because live Yahoo Finance data is unavailable.")
    return _build_synthetic_market_frame(symbol=symbol, period=period, interval=interval)


def get_gold_market_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
    last_error: Exception | None = None

    # Adjust period for 15m interval if not explicitly set
    if interval == "15m" and (period in (None, "6mo", "max") or period == ""):
        period = "1mo"  # Yahoo limit for 15m is 60d, but 1mo is safest

    for ticker in candidate_symbols(symbol):
        for candidate_period, candidate_interval in request_variants(period, interval):
            # For 15m, ensure period is not too long
            if candidate_interval == "15m" and candidate_period not in ["1mo", "2mo", "60d"]:
                candidate_period = "1mo"
            for raw_df in _download_variants(
                ticker=ticker,
                period=candidate_period,
                interval=candidate_interval,
            ):
                try:
                    if raw_df is None or raw_df.empty:
                        last_error = ValueError(
                            "Yahoo Finance returned an empty dataset "
                            f"for ticker={ticker}, period={candidate_period}, interval={candidate_interval}"
                        )
                        continue

                    df = _normalize_market_frame(raw_df)
                    # Ensure timestamp is in ISO format and sorted ascending
                    if "timestamp" in df.columns:
                        # Convert to UTC and ISO string
                        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                        df = df.sort_values("timestamp", ascending=True).reset_index(drop=True)
                    if not df.empty:
                        logger.info(
                            "Market data loaded successfully: request_symbol=%s resolved_ticker=%s requested_period=%s requested_interval=%s used_period=%s used_interval=%s rows=%s",
                            symbol,
                            ticker,
                            period,
                            interval,
                            candidate_period,
                            candidate_interval,
                            len(df),
                        )
                        return df
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Market data normalization failed for ticker=%s period=%s interval=%s: %s",
                        ticker,
                        candidate_period,
                        candidate_interval,
                        exc,
                    )

    detail = (
        f"No market data returned from yfinance for symbol={symbol}, period={period}, interval={interval}. "
        "Falling back to local/offline demo data because Yahoo Finance may be temporarily blocking the request, the interval may be unavailable, or the machine may have no outbound internet access."
    )
    if last_error is not None:
        detail = f"{detail} Last error: {last_error}"
    logger.warning(detail)
    return _build_fallback_market_frame(symbol=symbol, period=period, interval=interval)
