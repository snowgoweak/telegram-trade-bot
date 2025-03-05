from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 5432
    NAME: str = "mydb"
    USER_NAME: str = "myuser"
    PASSWORD: str = "mypassword"


class Settings(BaseSettings):
    DATABASE: DatabaseSettings = DatabaseSettings()
    ENCRYPTION_KEY: bytes = b"9kMeuf46Mdf1dGXHb_snUoxGPKolNRIJqR4JVrdxrV0="
    TON_API_KEY: str = (
        "AG7ABP5LK3VBS2YAAAAIUJCB4HIZCXUKZSYPN5OIARDOZRABG4JFZR3VJQASVZKWFTNHYOQ"
    )

    class Config:
        env_file = ".env"


settings = Settings()
