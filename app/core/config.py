from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Drafft API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/v1"
    log_level: str = "INFO"
    storage_backend: str = "local"
    local_storage_path: str = "./storage"
    default_style_preset: str = "finance_clean"
    enable_mock_providers: bool = True
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-5"
    elevenlabs_api_key: str | None = None
    webhook_timeout_seconds: int = 10
    # Firebase / Firestore
    firebase_project_id: str = ""
    google_application_credentials: str = ""  # path to service-account JSON
    # Set to False to skip token verification in local dev (uses "dev-user" uid)
    enable_auth: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
