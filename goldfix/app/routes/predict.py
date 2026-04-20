from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.response_models import PredictResponse
from app.services.predict_service import generate_prediction

router = APIRouter(tags=["predict"])


@router.get("/predict/gold", response_model=PredictResponse)
def predict_gold(
    symbol: str = Query(default=settings.SYMBOL),
    period: str = Query(default=settings.DEFAULT_PERIOD),
    interval: str = Query(default=settings.DEFAULT_INTERVAL),
):
    try:
        return generate_prediction(symbol=symbol, period=period, interval=interval)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
