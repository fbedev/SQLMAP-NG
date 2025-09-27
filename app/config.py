from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SQLMap Pro"
    api_prefix: str = "/api"
    port: int = 8000
    data_dir: Path = Path("data")
    authorization_subdir: str = "authorizations"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / settings.authorization_subdir).mkdir(parents=True, exist_ok=True)
