from __future__ import annotations

import pandas as pd

from app.core.config import settings
from app.services.indicator_service import enrich_indicators
from app.services.news_service import get_news_snapshot


def build_feature_dataframe(df: pd.DataFrame, symbol: str) -> tuple[pd.DataFrame, dict]:
    enriched = enrich_indicators(df)
    news_snapshot = get_news_snapshot(symbol)

    features = pd.DataFrame()
    features["Close"] = pd.to_numeric(enriched["Close"], errors="coerce")
    features["News_Sentiment"] = float(news_snapshot["sentiment"])

    meta = {
        "news_sentiment": float(news_snapshot["sentiment"]),
        "news_headlines": news_snapshot["headlines"],
        "latest_indicators": {
            "rsi14": float(enriched["RSI14"].iloc[-1]),
            "ema12": float(enriched["EMA12"].iloc[-1]),
            "ema26": float(enriched["EMA26"].iloc[-1]),
            "macd": float(enriched["MACD"].iloc[-1]),
            "macd_signal": float(enriched["MACD_Signal"].iloc[-1]),
            "macd_hist": float(enriched["MACD_Hist"].iloc[-1]),
            "rolling_vol20": float(enriched["RollingVol20"].iloc[-1]),
            "drawdown": float(enriched["Drawdown"].iloc[-1]),
        },
    }
    return features.dropna().reset_index(drop=True), meta


def get_latest_feature_window(df: pd.DataFrame, symbol: str) -> tuple[pd.DataFrame, dict]:
    features, meta = build_feature_dataframe(df, symbol)
    if len(features) < settings.MODEL_SEQUENCE_LENGTH:
        raise ValueError(
            f"Not enough rows for model. Need at least {settings.MODEL_SEQUENCE_LENGTH}, got {len(features)}"
        )
    return features.tail(settings.MODEL_SEQUENCE_LENGTH).reset_index(drop=True), meta


def get_latest_feature_window_with_fallback(
    primary_df: pd.DataFrame,
    symbol: str,
    *,
    fallback_loader=None,
) -> tuple[pd.DataFrame, dict]:
    try:
        window, meta = get_latest_feature_window(primary_df, symbol)
        meta["input_adjusted"] = False
        return window, meta
    except ValueError as exc:
        if fallback_loader is None:
            raise
        fallback_df, fallback_period, fallback_interval = fallback_loader()
        window, meta = get_latest_feature_window(fallback_df, symbol)
        meta["input_adjusted"] = True
        meta["input_adjust_reason"] = str(exc)
        meta["used_period"] = fallback_period
        meta["used_interval"] = fallback_interval
        return window, meta
