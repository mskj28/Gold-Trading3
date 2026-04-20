from __future__ import annotations

import pandas as pd


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_macd(close: pd.Series) -> pd.DataFrame:
    ema12 = compute_ema(close, 12)
    ema26 = compute_ema(close, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame(
        {
            "EMA12": ema12,
            "EMA26": ema26,
            "MACD": macd,
            "MACD_Signal": signal,
            "MACD_Hist": hist,
        }
    )


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    close = pd.to_numeric(enriched["Close"], errors="coerce")
    macd_df = compute_macd(close)
    enriched = pd.concat([enriched.reset_index(drop=True), macd_df.reset_index(drop=True)], axis=1)
    enriched["RSI14"] = compute_rsi(close)
    enriched["Return"] = close.pct_change().fillna(0.0)
    enriched["RollingVol20"] = enriched["Return"].rolling(20).std().fillna(0.0)
    enriched["PeakClose"] = close.cummax()
    enriched["Drawdown"] = ((close - enriched["PeakClose"]) / enriched["PeakClose"]).fillna(0.0)
    return enriched


def classify_rsi(rsi_value: float) -> str:
    if rsi_value <= 30:
        return "oversold"
    if rsi_value >= 70:
        return "overbought"
    return "neutral"


def classify_macd(macd_value: float, signal_value: float) -> str:
    return "bullish" if macd_value >= signal_value else "bearish"
