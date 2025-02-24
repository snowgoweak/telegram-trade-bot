from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 5432
    name: str = "mydb"
    user: str = "myuser"
    password: str = "mypassword"


class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    ENCRYPTION_KEY: bytes = b"9kMeuf46Mdf1dGXHb_snUoxGPKolNRIJqR4JVrdxrV0="

    class Config:
        env_file = ".env"


settings = Settings()
