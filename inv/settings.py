"""Application settings using pydantic-settings and platformdirs."""

from pathlib import Path

import platformdirs
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppDirs:
    """Cross-platform directory paths using platformdirs."""

    APP_NAME = "inventory"

    @classmethod
    def config_dir(cls) -> Path:
        """User config directory (XDG_CONFIG_HOME on Linux, ~/Library/Preferences on macOS, etc.)."""
        return Path(platformdirs.user_config_dir(cls.APP_NAME))

    @classmethod
    def data_dir(cls) -> Path:
        """User data directory (XDG_DATA_HOME on Linux, ~/Library/Application Support on macOS, etc.)."""
        return Path(platformdirs.user_data_dir(cls.APP_NAME))

    @classmethod
    def cache_dir(cls) -> Path:
        """User cache directory."""
        return Path(platformdirs.user_cache_dir(cls.APP_NAME))

    @classmethod
    def log_dir(cls) -> Path:
        """User log directory."""
        return Path(platformdirs.user_log_dir(cls.APP_NAME))

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create all required directories if they don't exist."""
        cls.config_dir().mkdir(parents=True, exist_ok=True)
        cls.data_dir().mkdir(parents=True, exist_ok=True)
        cls.cache_dir().mkdir(parents=True, exist_ok=True)
        cls.log_dir().mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="INVENTORY_",
        case_sensitive=False,
    )

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8765
    reload: bool = False

    # Database
    database_url: str | None = None  # Will use XDG data dir SQLite if not set

    # Logging
    log_level: str = "info"

    @property
    def db_path(self) -> Path:
        """Get the SQLite database path."""
        if self.database_url:
            # Parse sqlite:/// URLs
            if self.database_url.startswith("sqlite:///"):
                return Path(self.database_url[10:])
            return Path(self.database_url)
        # Default: use XDG data directory
        return AppDirs.data_dir() / "inventory.db"

    def __init__(self, **data):  # type: ignore
        """Initialize settings and ensure directories exist."""
        super().__init__(**data)
        AppDirs.ensure_dirs()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return Settings()
