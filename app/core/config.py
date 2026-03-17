from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    project_name: str = "Event Scraper API"
    version: str = "1.0.0"

    # Database Configuration
    database_url: str = Field(default="sqlite:////app/events.db", description="Database URI")

    # Scheduler Configuration
    schedule_timezone: str = Field(default="Europe/Berlin", description="Timezone for the scheduler")
    monday_crawl_hour: int = 4  # Monday at 04:00 AM
    monday_crawl_minute: int = 0
    thursday_crawl_hour: int = 4 # Thursday at 04:00 AM
    thursday_crawl_minute: int = 0

    # Scraper configurations
    default_location: str = "Berlin"

    # Define these in environment if you have fallback solutions like Jina API or proxies
    jina_api_key: str | None = None
    firecrawl_api_key: str | None = None
    proxy_url: str | None = None
    proxy_auth: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='ignore')

settings = Settings()
