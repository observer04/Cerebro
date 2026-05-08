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
    rate_limit_global: str = Field(
        default="10000/second", alias="RATE_LIMIT_GLOBAL"
    )
    rate_limit_per_ip: str = Field(default="1000/second", alias="RATE_LIMIT_PER_IP")
    throughput_window_seconds: int = Field(
        default=5, alias="THROUGHPUT_WINDOW_SECONDS"
    )
    throughput_counter_key: str = Field(
        default="metrics:signals_count", alias="THROUGHPUT_COUNTER_KEY"
    )
    throughput_rate_key: str = Field(
        default="metrics:signals_rate", alias="THROUGHPUT_RATE_KEY"
    )
    throughput_lock_key: str = Field(
        default="metrics:throughput_lock", alias="THROUGHPUT_LOCK_KEY"
    )

    model_config = SettingsConfigDict(env_prefix="", populate_by_name=True)


settings = Settings()
