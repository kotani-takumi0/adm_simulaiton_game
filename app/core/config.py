# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    CORS_ORIGINS: str = "http://localhost:3000"

    # ★ ゲームの固定パラメータ（サーバ側で決める）
    GAME_YEARS: int = 5
    GAME_EVENTS_PER_YEAR: int = 12
    GAME_BUDGET_PER_YEAR: int = 150_000_000_000  # 1,500億円
    GAME_CURRENCY: str = "JPY"  # 返却時の明示に使える

    # ★ 予算推定のハイパーパラメータ
    TOPK: int = 5
    TAU: float = 0.08
    ALPHA: float = 0.5
    BETA: float = 0.5

    # ★ 埋め込み設定
    EMBEDDING_PROVIDER: str = "dummy"  # "openai" or "dummy"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None  # e.g. Azure/OpenAI-compatible endpoint

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
