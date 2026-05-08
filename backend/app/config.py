from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ims_env: str = Field(default="local", alias="IMS_ENV")
    postgres_dsn: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/ims",
        alias="POSTGRES_DSN",
    )
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017/ims", alias="MONGODB_URI"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS"
    )

    model_config = SettingsConfigDict(env_prefix="", populate_by_name=True)


settings = Settings()
