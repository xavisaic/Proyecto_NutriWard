from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NutriWard API"
    app_env: str = "development"
    app_debug: bool = True
    database_url: str = "postgresql+psycopg://nutriward:nutriward@localhost:5432/nutriward"
    jwt_secret_key: str = "development-only-secret-change-before-production"
    access_token_expire_minutes: int = 30
    auth_cookie_name: str = "nutriward_access_token"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    demo_user_password: str = "NutriWard-Demo-2026!"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def cookie_secure(self) -> bool:
        return self.app_env.lower() not in {"development", "test"}


settings = Settings()
