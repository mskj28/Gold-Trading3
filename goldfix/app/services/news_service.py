from __future__ import annotations

from typing import Any

import yfinance as yf

from app.core.config import settings
from app.utils.logger import send_log


POSITIVE_KEYWORDS = {
    "rate cut": 0.8,
    "cuts rates": 0.8,
    "geopolitical tension": 0.7,
    "safe haven": 0.6,
    "inflation cools": 0.5,
    "recession fears": 0.3,
    "central bank buying": 0.8,
}
NEGATIVE_KEYWORDS = {
    "strong dollar": -0.8,
    "hawkish": -0.6,
    "rate hike": -0.8,
    "yields rise": -0.5,
    "treasury yields": -0.4,
    "risk-on": -0.3,
}


def _score_text(text: str) -> float:
    lowered = text.lower()
    score = 0.0
    for phrase, weight in POSITIVE_KEYWORDS.items():
        if phrase in lowered:
            score += weight
    for phrase, weight in NEGATIVE_KEYWORDS.items():
        if phrase in lowered:
            score += weight
    return score


def get_news_snapshot(symbol: str) -> dict[str, Any]:
    ticker = "GC=F" if symbol.upper() == "XAUUSD" else symbol
    try:
        news_items = yf.Ticker(ticker).news or []
    except Exception as exc:
        logger.warning("Failed to fetch news for %s: %s", symbol, exc)
        news_items = []

    headlines: list[str] = []
    scores: list[float] = []
    for item in news_items[: settings.NEWS_HEADLINE_LIMIT]:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        headlines.append(title)
        scores.append(_score_text(title))

    if not scores:
        return {"sentiment": 0.0, "headlines": []}

    avg_sentiment = max(-1.0, min(1.0, sum(scores) / max(len(scores), 1)))
    return {"sentiment": round(avg_sentiment, 4), "headlines": headlines}


def get_news_sentiment(symbol: str) -> float:
    snapshot = get_news_snapshot(symbol)
    logger.info("News sentiment for %s: %.4f", symbol, snapshot["sentiment"])
    return float(snapshot["sentiment"])
