from __future__ import annotations

from app.core.config import settings
from app.services.feature_service import get_latest_feature_window_with_fallback
from app.services.indicator_service import classify_macd, classify_rsi
from app.services.market_service import get_gold_market_data
from app.services.predict_service import decide_signal
from app.services.risk_service import build_backtest_preview, build_trade_risk_overlay
from app.services.ai_service import predict_price


def build_gold_analysis(symbol: str, period: str, interval: str, capital: float | None = None) -> dict:
    capital = capital or settings.DEFAULT_CAPITAL
    market_df = get_gold_market_data(symbol=symbol, period=period, interval=interval)
    feature_window, meta = get_latest_feature_window_with_fallback(
        market_df,
        symbol,
        fallback_loader=lambda: (
            get_gold_market_data(
                symbol=symbol,
                period=settings.DEFAULT_PERIOD,
                interval=settings.DEFAULT_INTERVAL,
            ),
            settings.DEFAULT_PERIOD,
            settings.DEFAULT_INTERVAL,
        ),
    )

    current_price = float(feature_window["Close"].iloc[-1])
    ai_result = predict_price(feature_window=feature_window, current_price=current_price)
    predicted_price = float(ai_result["predicted_price"])
    expected_change = predicted_price - current_price
    expected_change_pct = (expected_change / current_price) * 100 if current_price else 0.0

    indicators = meta["latest_indicators"]
    risk_overlay = build_trade_risk_overlay(
        capital=capital,
        current_price=current_price,
        predicted_price=predicted_price,
        rolling_volatility=float(indicators["rolling_vol20"]),
        current_drawdown=float(indicators["drawdown"]),
    )

    signal = decide_signal(current_price, predicted_price)
    if risk_overlay["trading_blocked"]:
        signal = "HOLD"

    recommendation = {
        "action": signal,
        "reason": {
            "price_model": "bullish" if predicted_price > current_price else "bearish",
            "rsi_state": classify_rsi(float(indicators["rsi14"])),
            "macd_state": classify_macd(float(indicators["macd"]), float(indicators["macd_signal"])),
            "news_sentiment_direction": "bullish" if meta["news_sentiment"] > 0 else "bearish" if meta["news_sentiment"] < 0 else "neutral",
        },
        "position": {
            "capital": capital,
            "max_position_pct": settings.MAX_POSITION_PCT,
            "suggested_position_value": risk_overlay["suggested_position_value"],
            "suggested_units": risk_overlay["suggested_units"],
        },
    }

    state = {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "used_period": meta.get("used_period", period),
        "used_interval": meta.get("used_interval", interval),
        "input_adjusted": bool(meta.get("input_adjusted", False)),
        "current_price": current_price,
        "news_sentiment": meta["news_sentiment"],
        "headlines": meta["news_headlines"],
        "indicators": indicators,
    }
    prediction = {
        "predicted_price": predicted_price,
        "expected_change": round(expected_change, 6),
        "expected_change_pct": round(expected_change_pct, 6),
        "confidence": float(ai_result["confidence"]),
        "source": ai_result["source"],
    }
    risk = {
        **risk_overlay,
        "backtest_preview": build_backtest_preview(market_df),
    }
    return {"symbol": symbol, "state": state, "prediction": prediction, "risk": risk, "recommendation": recommendation}
