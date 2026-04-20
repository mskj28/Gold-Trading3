from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str


class MarketResponse(BaseModel):
    symbol: str
    period: str
    interval: str
    rows: int
    latest_time: str | None
    current_price: float | None


class PredictResponse(BaseModel):
    symbol: str
    current_price: float
    predicted_price: float
    expected_change: float
    expected_change_pct: float
    signal: str
    confidence: float
    source: str
    input_sequence_length: int
    input_features: list[str]
    indicators: dict[str, float | str | None]
    news_sentiment: float
    current_price_thb: float
    predicted_price_thb: float
    usdthb: float
    gold_thai: float
    buy_price: float
    sell_price: float

class AnalysisResponse(BaseModel):
    symbol: str
    state: dict[str, Any]
    prediction: dict[str, Any]
    risk: dict[str, Any]
    recommendation: dict[str, Any]


class BacktestPreviewResponse(BaseModel):
    symbol: str
    period: str
    interval: str
    rows: int
    metrics: dict[str, float]
