"""Application settings, read from environment variables (and backend/.env)."""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"  # development | testing | production
    database_url: str = ""
    secret_key: str = ""
    jwt_secret_key: str = ""

    frontend_url: str = "http://localhost:5173"
    cors_origins: str = ""

    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    access_token_minutes: int = 15
    refresh_token_days: int = 14
    password_reset_minutes: int = 30
    invite_token_minutes: int = 3 * 24 * 60

    max_failed_logins: int = 5
    lockout_minutes: int = 15
    login_rate_limit: str = "10/minute"

    seed_demo_password: str = ""

    # Documents (uploads are stored on local disk)
    upload_dir: str = "uploads"
    max_upload_mb: int = 5

    # ---- AI assistant
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    llm_effort: str = ""
    llm_timeout_seconds: float = 45
    llm_max_retries: int = 1
    llm_max_output_tokens: int = 8000
    llm_anthropic_fallbacks: str = "default"  # server-side refusal fallback; empty turns it off
    assistant_max_input_chars: int = 2000
    assistant_turn_seconds: int = 90
    assistant_max_tool_rounds: int = 5
    assistant_history_messages: int = 20
    assistant_max_messages_per_conversation: int = 200
    assistant_action_ttl_minutes: int = 60
    assistant_retention_days: int = 30
    assistant_chat_rate_limit: str = "12/minute;200/day"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _check(self):
        if self.app_env == "testing":
            return self
        missing = [k for k in ("database_url", "secret_key", "jwt_secret_key") if not getattr(self, k)]
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(m.upper() for m in missing)} (see backend/.env.example)")
        if self.is_production:
            if len(self.secret_key) < 32 or len(self.jwt_secret_key) < 32:
                raise ValueError("SECRET_KEY and JWT_SECRET_KEY must be at least 32 characters in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
