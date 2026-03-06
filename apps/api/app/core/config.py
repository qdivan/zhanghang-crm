from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "账航·一帆财税 API"
    environment: str = "dev"
    database_url: str = "sqlite+pysqlite:///./daizhang.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    cors_allow_origins: str = "*"
    bootstrap_demo_data: bool = False
    bootstrap_demo_password: str = "Daizhang#2026!"
    reset_db_on_startup: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        parsed = [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]
        return parsed or ["*"]


settings = Settings()
