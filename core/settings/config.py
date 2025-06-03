# Import necessary classes from pydantic_settings for configuration management
import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Set DEBUG_ENV to True to ensure .env file is loaded
DEBUG_ENV = os.environ.get('DEBUG', 'True').lower() == 'true'


# Define a Settings class to manage application configuration, loading from environment variables or .env file in debug mode
class Settings(BaseSettings):
    # Configuration for loading environment variables
    model_config = SettingsConfigDict(
        env_file='.env' if DEBUG_ENV else None,  # Use .env file only if DEBUG is True in the environment
        env_file_encoding='utf-8',  # Encoding for the .env file
        case_sensitive=True,  # Make environment variable names case-sensitive
    )

    # Django settings
    DEBUG: bool = False  # Enable/disable debug mode
    ALLOWED_HOSTS: List[str] = ["localhost"]  # Default list of allowed hostnames
    SECRET_KEY: str = ''  # Secret key for cryptographic signing
    REDIS_PASSWORD: str = ''  # Password for Redis connection
    REDIS_HOST: str = 'localhost'  # Hostname for Redis server
    REDIS_PORT: int = 6379  # Port for Redis server
    # PostgreSQL settings
    POSTGRES_NAME: str = ''  # Database name
    POSTGRES_USER: str = ''  # Database user
    POSTGRES_PASSWORD: str = ''  # Database password
    POSTGRES_HOST: str = 'localhost'  # Database host

    SIGNATURE_AUTH_SECRET_KEY: str = ''  # Secret key for signature authentication
    INTERNAL_IPS: List[str] = ["localhost"]
    CONFIG_CACHE_TIMEOUT: int = 3600

# Instantiate the settings object to be used throughout the application
settings = Settings()
