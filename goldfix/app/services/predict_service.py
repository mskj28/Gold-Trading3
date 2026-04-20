from __future__ import annotations

from app.utils.logger import send_log

from app.core.config import settings
from app.services.ai_service import predict_price
from app.services.feature_service import get_latest_feature_window_with_fallback
from app.services.market_service import get_gold_market_data
from app.services.fx_service import get_usdthb_rate


def decide_signal(current_price: float, predicted_price: float) -> str:
    diff_pct = ((predicted_price - current_price) / current_price) * 100
    if diff_pct > 0.15:
        return "BUY"
    if diff_pct < -0.15:
        return "SELL"
    return "HOLD"


def generate_prediction(symbol: str, period: str, interval: str) -> dict:
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

    # ===== ราคาทอง USD =====
    
    current_price = float(feature_window["Close"].iloc[-1])
    ai_result = predict_price(feature_window=feature_window, current_price=current_price)
    predicted_price = float(ai_result["predicted_price"])

    expected_change = predicted_price - current_price
    expected_change_pct = (expected_change / current_price) * 100 if current_price != 0 else 0.0

    indicators = meta["latest_indicators"]

    # ===== สัญญาณ =====
    action = decide_signal(current_price, predicted_price)

    # ===== reason =====
    if action == "BUY":
        reason = f"AI predicts +{expected_change_pct:.2f}%"
    elif action == "SELL":
        reason = f"AI predicts {expected_change_pct:.2f}%"
    else:
        reason = "No strong signal"

    # ===== 🔥 แปลงเป็นเงินบาท =====
    try:
        usdthb = get_usdthb_rate()
    except Exception:
        usdthb = 35.0  # fallback กันพัง

    current_price_thb = round(current_price * usdthb, 2) #แปลงตรง
    predicted_price_thb = round(predicted_price * usdthb, 2)
    gold_thai = round(current_price_thb * 0.965, 2) #ราคาทองไทยจริง (approx)
    buy_price = gold_thai + 200   # ร้านขายให้เรา
    sell_price = gold_thai - 200  # ร้านรับซื้อ
    # ===== 🔥 ยิง log เป็นเงินบาท =====
    send_log(action, current_price_thb, reason)

    # ===== return =====
    return {
        "symbol": symbol,

        # USD
        "current_price": current_price,
        "predicted_price": predicted_price,
        "expected_change": float(expected_change),
        "expected_change_pct": float(expected_change_pct),

        # 🔥 THB (เพิ่มใหม่)
        "current_price_thb": current_price_thb,
        "predicted_price_thb": predicted_price_thb,
        "usdthb": usdthb,
        "gold_thai": gold_thai,
        "buy_price": buy_price,
        "sell_price": sell_price,

        # 🔥 ต้องมีทั้งคู่ (กัน error)
        "signal": action,
        "action": action,


        "confidence": float(ai_result["confidence"]),
        "source": ai_result["source"],
        "input_sequence_length": settings.MODEL_SEQUENCE_LENGTH,
        "input_features": settings.model_feature_list,
        "input_adjusted": bool(meta.get("input_adjusted", False)),
        "used_period": meta.get("used_period", period),
        "used_interval": meta.get("used_interval", interval),

        "indicators": {
            "rsi14": round(float(indicators["rsi14"]), 6),
            "macd": round(float(indicators["macd"]), 6),
            "macd_signal": round(float(indicators["macd_signal"]), 6),
            "macd_hist": round(float(indicators["macd_hist"]), 6),
        },

        "news_sentiment": float(meta["news_sentiment"]),
        
    }
