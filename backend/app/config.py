from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / '.env',
        env_file_encoding='utf-8', extra='ignore',
    )
    groq_api_key: SecretStr = SecretStr('')
    groq_model: str = 'openai/gpt-oss-20b'
    frontend_url: str = 'http://localhost:5173'
    scraper_user_agent: str = 'AIWebScraper/0.1 (https://github.com/Kallan0/WebScraper)'

    @field_validator('frontend_url')
    @classmethod
    def normalize_frontend_origin(cls, value: str) -> str:
        return value.strip().rstrip('/')

    request_timeout: float = Field(default=20.0, gt=0)
    groq_timeout: float = Field(default=30.0, gt=0)
    max_response_bytes: int = Field(default=10_000_000, gt=0)
    max_scraped_characters: int = Field(default=50_000, gt=0)
    max_summary_characters: int = Field(default=12_000, gt=0)
    max_redirects: int = Field(default=5, ge=0, le=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
