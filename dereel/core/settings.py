from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    telegram_bot_token: str
    telegram_chat_id: str

    log_level: str = "INFO"
    data_dir: str = "./data"
    storage_type: str = "json"



settings = Settings()