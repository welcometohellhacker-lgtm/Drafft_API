from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Drafft API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/v1"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./drafft.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_backend: str = "local"
    local_storage_path: str = "./storage"
    default_style_preset: str = "finance_clean"
    enable_mock_providers: bool = True
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    webhook_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
