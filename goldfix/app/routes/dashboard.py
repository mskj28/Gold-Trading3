from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.services.dashboard_service import build_dashboard_payload

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/gold")
def get_dashboard_gold(
    symbol: str = Query(default=settings.SYMBOL),
    period: str = Query(default=settings.DEFAULT_PERIOD),
    interval: str = Query(default=settings.DEFAULT_INTERVAL),
    capital: float = Query(default=settings.DEFAULT_CAPITAL, gt=0),
):
    try:
        return build_dashboard_payload(symbol=symbol, period=period, interval=interval, capital=capital)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}") from exc
