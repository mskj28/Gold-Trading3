from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.response_models import MarketResponse
from app.services.market_service import get_gold_market_data

router = APIRouter(tags=["market"])


@router.get("/market/gold", response_model=MarketResponse)
def get_market_gold(
    symbol: str = Query(default=settings.SYMBOL, description="Market symbol, e.g. XAUUSD"),
    period: str = Query(default=settings.DEFAULT_PERIOD, description="Data period, e.g. 1mo for 15m interval"),
    interval: str = Query(default=settings.DEFAULT_INTERVAL, description="Timeframe interval, e.g. 15m, 1d"),
):
    """
    Get gold market data. Default interval is 15m (intraday). You can override period/interval via query params.
    """
    try:
        df = get_gold_market_data(symbol=symbol, period=period, interval=interval)
        latest_time = str(df["timestamp"].iloc[-1]) if "timestamp" in df.columns else None
        current_price = float(df["Close"].iloc[-1]) if "Close" in df.columns else None
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "rows": len(df),
            "latest_time": latest_time,
            "current_price": current_price,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/market-data")
def get_market_data(
    symbol: str = Query(default=settings.SYMBOL),
    period: str = Query(default=settings.DEFAULT_PERIOD),
    interval: str = Query(default=settings.DEFAULT_INTERVAL),
):
    try:
        df = get_gold_market_data(symbol=symbol, period=period, interval=interval)
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "rows": len(df),
            "columns": list(df.columns),
            "data": df.tail(10).to_dict(orient="records"),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc