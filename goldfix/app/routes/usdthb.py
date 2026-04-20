import yfinance as yf
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from app.utils.logger import get_logger

logger = get_logger(__name__)

usdthb_router = APIRouter(tags=["fx"])


def _fetch_usdthb_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if df is None or df.empty:
        df = yf.download(ticker, period=period, interval=interval, progress=False, threads=False)
    if df is None or df.empty:
        raise ValueError(f"No data returned from Yahoo Finance for {ticker} using period={period}, interval={interval}")
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=0, drop=True)
    return df


@usdthb_router.get("/usdthb")
def get_usdthb_rate(
    interval: str = Query("5m", description="Interval for FX data, e.g. 1m, 5m, 15m"),
    period: str = Query("1d", description="Period for FX data, e.g. 1d, 5d, 1mo"),
):
    """
    Get the latest USD/THB exchange rate from Yahoo Finance.
    """
    ticker = "USDTHB=X"
    try:
        df = _fetch_usdthb_history(ticker, period, interval)
        last_row = df.iloc[-1]
        close_value = last_row.get("Close") if isinstance(last_row, pd.Series) else None
        if close_value is None:
            close_value = last_row.get("close") if isinstance(last_row, pd.Series) else None
        if close_value is None:
            close_value = float(last_row.iloc[-1])
        rate = float(close_value)
        timestamp = pd.to_datetime(df.index[-1], utc=True).isoformat()
        return {
            "symbol": ticker,
            "rate": rate,
            "timestamp": timestamp,
        }
    except Exception as exc:
        logger.warning(f"Failed to fetch USDTHB rate: {exc}")
        raise HTTPException(status_code=503, detail=f"Could not fetch USDTHB rate: {exc}")
