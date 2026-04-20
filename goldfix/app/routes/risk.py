from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.response_models import BacktestPreviewResponse
from app.services.market_service import get_gold_market_data
from app.services.risk_service import build_backtest_preview

router = APIRouter(tags=["risk"])


@router.get("/risk/backtest-preview", response_model=BacktestPreviewResponse)
def risk_backtest_preview(
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
            "metrics": build_backtest_preview(df),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
