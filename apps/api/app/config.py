from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://maelstromhub:maelstromhub@localhost:5432/maelstromhub"
    redis_url: str = "redis://localhost:6379/0"
    service_name: str = "maelstromhub-api"
    promotion_max_drawdown_threshold: float = -0.20
    promotion_min_trade_count: int = 1
    promotion_min_total_return: float = -0.05
    regime_volatility_low_percentile: float = 0.30
    regime_volatility_high_percentile: float = 0.70
    regime_atr_low_percentile: float = 0.30
    regime_atr_high_percentile: float = 0.70
    regime_thin_liquidity_volume_percentile: float = 0.20
    regime_return_epsilon: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
