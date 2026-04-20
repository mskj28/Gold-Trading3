from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Gold Trading AI API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    USE_MOCK_MODEL: bool = False
    SYMBOL: str = "XAUUSD"
    DEFAULT_PERIOD: str = "1mo"  # 1 month for 15m interval (Yahoo limit)
    DEFAULT_INTERVAL: str = "15m"  # Default to 15m timeframe
    MODEL_PATH: str = "app/backtest/backend_model/xauusd_polygon_lstm_cv_final.keras"
    FEATURE_SCALER_PATH: str = "app/backtest/backend_model/polygon_feature_scaler.pkl"
    PRICE_SCALER_PATH: str = "app/backtest/backend_model/polygon_price_scaler.pkl"
    MODEL_SEQUENCE_LENGTH: int = 60
    MODEL_FEATURES: str = "Close,News_Sentiment"
    MAX_POSITION_PCT: float = 0.10
    MAX_DRAWDOWN_LIMIT: float = 0.05
    KELLY_FRACTION: float = 0.50
    DEFAULT_CAPITAL: float = 10000.0
    NEWS_LOOKBACK_DAYS: int = 3
    NEWS_HEADLINE_LIMIT: int = 8

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    @property
    def model_feature_list(self) -> list[str]:
        return [x.strip() for x in self.MODEL_FEATURES.split(",") if x.strip()]


settings = Settings()
