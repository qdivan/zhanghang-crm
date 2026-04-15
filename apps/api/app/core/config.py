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
    sso_enabled: bool = False
    sso_provider_label: str = "企业单点登录"
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: str = "openid profile email"
    app_public_base_url: str = "http://127.0.0.1:5173"
    oidc_post_logout_redirect_url: str = ""
    local_login_enabled: bool = True
    sso_flow_ttl_minutes: int = 10
    sso_exchange_ttl_minutes: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        parsed = [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]
        return parsed or ["*"]

    @property
    def oidc_scope_list(self) -> list[str]:
        parsed = [item.strip() for item in self.oidc_scopes.split() if item.strip()]
        return parsed or ["openid", "profile", "email"]

    @property
    def sso_ready(self) -> bool:
        return bool(
            self.sso_enabled
            and self.oidc_issuer.strip()
            and self.oidc_client_id.strip()
            and self.oidc_client_secret.strip()
            and self.app_public_base_url.strip()
        )

    @property
    def oidc_callback_url(self) -> str:
        base = self.app_public_base_url.rstrip("/")
        return f"{base}/api/v1/auth/sso/callback"

    @property
    def oidc_frontend_exchange_url(self) -> str:
        base = self.app_public_base_url.rstrip("/")
        return f"{base}/login/sso"

    @property
    def oidc_logout_redirect_url(self) -> str:
        configured = self.oidc_post_logout_redirect_url.strip()
        if configured:
            return configured
        return f"{self.app_public_base_url.rstrip('/')}/login"


settings = Settings()
