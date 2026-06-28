from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://maelstromhub:maelstromhub@localhost:5432/maelstromhub"
    redis_url: str = "redis://localhost:6379/0"
    service_name: str = "maelstromhub-api"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
