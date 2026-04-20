from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.response_models import AnalysisResponse
from app.services.analysis_service import build_gold_analysis

router = APIRouter(tags=["analysis"])


@router.get("/analysis/gold", response_model=AnalysisResponse)
def get_gold_analysis(
    symbol: str = Query(default=settings.SYMBOL),
    period: str = Query(default=settings.DEFAULT_PERIOD),
    interval: str = Query(default=settings.DEFAULT_INTERVAL),
    capital: float = Query(default=settings.DEFAULT_CAPITAL, gt=0),
):
    try:
        return build_gold_analysis(symbol=symbol, period=period, interval=interval, capital=capital)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
