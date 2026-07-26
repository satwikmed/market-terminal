from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Lumen"
    database_url: str = "sqlite+aiosqlite:///./plain_english.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    ai_provider: str = "auto"
    fred_api_key: str = ""
    news_api_key: str = ""
    # SEC EDGAR requires a descriptive User-Agent with a working contact address.
    # https://www.sec.gov/os/webmaster-faq#developers
    sec_user_agent: str = "Plain English Terminal (educational project) contact@plainenglishterminal.dev"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Regex alternative to cors_origins, e.g. for Vercel preview deployments.
    cors_origin_regex: str = ""
    price_poll_seconds: int = 45
    demo_mode: bool = False  # True = synthetic quotes; False = live yfinance
    enable_scheduler: bool = True
    quote_refresh_minutes: int = 10
    startup_refresh: bool = True
    # Shared secret for the manual data-refresh endpoint. Blank disables it.
    admin_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_ai_provider(self) -> str | None:
        if self.ai_provider == "openai" and self.openai_api_key:
            return "openai"
        if self.ai_provider == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        if self.ai_provider == "auto":
            if self.openai_api_key:
                return "openai"
            if self.anthropic_api_key:
                return "anthropic"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
