from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# config.py 位于 backend/app/core/，向上四层就是项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置，统一管理，统一从项目根目录的 .env 和环境变量读取。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-flash"
    dashscope_api_key: str | None = None
    embedding_model: str = "text-embedding-v4"
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma"
    top_k: int = Field(default=4, ge=1, le=20)

    @field_validator("chroma_dir")
    @classmethod
    def resolve_chroma_dir(cls, value: Path) -> Path:
        """相对路径统一以项目根目录为基准。"""
        return value if value.is_absolute() else PROJECT_ROOT / value


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免每个请求重复读取环境变量。"""
    return Settings()
