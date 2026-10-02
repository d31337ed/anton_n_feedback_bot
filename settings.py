from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "prod"

    bot_token: str
    chat_id: str
    error_topic_id: int

    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0

    api_id: int
    api_hash: str
    chat_peer_id: int

    @property
    def bot_id(self) -> int:
        return int(self.bot_token.split(":")[0])


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
