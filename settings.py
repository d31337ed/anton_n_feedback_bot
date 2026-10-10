from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", secrets_dir="/run/secrets")

    app_env: str = "prod"

    bot_token: str
    chat_id: str
    error_topic_id: int

    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0

    # Comma-separated user IDs. Empty = no restriction (prod default).
    allowed_user_ids: str = ""

    @property
    def bot_id(self) -> int:
        return int(self.bot_token.split(":")[0])

    @property
    def allowed_user_ids_set(self) -> set[int]:
        return {int(uid) for uid in self.allowed_user_ids.split(",") if uid.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
