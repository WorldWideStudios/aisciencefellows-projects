from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://aeo:aeo@db:5432/aeo"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    MODEL_MAIN: str = "perplexity/sonar-pro"
    MODEL_AUX: str = "openai/gpt-4o-mini"

    OPENROUTER_APP_NAME: str = "AEO Grader"
    OPENROUTER_SITE_URL: str = "http://localhost:3000"

    FRONTEND_ORIGIN: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"


settings = Settings()
