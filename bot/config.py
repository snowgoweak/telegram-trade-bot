from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str = "1100378954:AAFhaE-fdqJI2KiUPHikCxMshzZ7JeDTPQw"
    SERVICE_URL: str = "http://127.0.0.1:8000"

    class Config:
        env_file = ".env"


settings = Settings()
