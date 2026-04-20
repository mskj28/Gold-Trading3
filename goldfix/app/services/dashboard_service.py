from __future__ import annotations

from app.core.config import settings
from app.services.analysis_service import build_gold_analysis


def _build_reason_text(analysis: dict) -> str:
    pred = analysis["prediction"]
    rec = analysis["recommendation"]
    state = analysis["state"]
    reason = rec["reason"]
    return (
        f"Price model: {reason['price_model']} | "
        f"RSI: {reason['rsi_state']} | "
        f"MACD: {reason['macd_state']} | "
        f"News: {reason['news_sentiment_direction']} | "
        f"Expected change: {pred['expected_change_pct']:.4f}%"
    )


def _build_news_items(headlines: list[str], sentiment: float) -> list[dict]:
    news_sentiment = "neutral"
    if sentiment > 0:
        news_sentiment = "positive"
    elif sentiment < 0:
        news_sentiment = "negative"
    items = []
    for title in headlines[:5]:
        items.append({
            "title": title,
            "summary": "ข่าวที่ใช้ประกอบ sentiment analysis สำหรับสัญญาณทองคำ",
            "sentiment": news_sentiment,
            "url": "https://finance.yahoo.com/quote/GC%3DF/news",
        })
    return items


def build_dashboard_payload(symbol: str, period: str, interval: str, capital: float | None = None) -> dict:
    analysis = build_gold_analysis(symbol=symbol, period=period, interval=interval, capital=capital)
    action = analysis["recommendation"]["action"]
    confidence = float(analysis["prediction"]["confidence"])
    reason_text = _build_reason_text(analysis)
    headlines = analysis["state"].get("headlines", [])
    sentiment = float(analysis["state"].get("news_sentiment", 0.0))

    return {
        "symbol": symbol,
        "prediction": {
            "action": action,
            "confidence": confidence,
            "reason": reason_text,
            "current_price": analysis["state"]["current_price"],
            "predicted_price": analysis["prediction"]["predicted_price"],
            "expected_change_pct": analysis["prediction"]["expected_change_pct"],
            "input_adjusted": bool(analysis["state"].get("input_adjusted", False)),
            "used_period": analysis["state"].get("used_period", period),
            "used_interval": analysis["state"].get("used_interval", interval),
            "source": analysis["prediction"]["source"],
        },
        "news": _build_news_items(headlines, sentiment),
        "state": analysis["state"],
        "risk": analysis["risk"],
        "recommendation": analysis["recommendation"],
        "meta": {
            "model_sequence_length": settings.MODEL_SEQUENCE_LENGTH,
            "model_features": settings.model_feature_list,
        },
    }
