from pathlib import Path
from pydantic import Field
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.settings.app_version import __version__
from app.settings.app_env_path import get_env_paths

class Settings(BaseSettings):  
    """  
    Configuración centralizada de la app
    """  
    # ------------ APP INFO ------------  
    APP_NAME: str = "BotDownloader"  
    APP_VERSION: str = __version__

    # ------------ DIRECTORIOS ------------  
    HOME_DIR: Path = Path.home() / f".{APP_NAME.lower()}"
    SETTINGS_DIR: Path = HOME_DIR / "settings"
    CACHE_DIR: Path = HOME_DIR / "cache"
    LOGS_DIR: Path = HOME_DIR / "logs"
    BIN_DIR: Path = HOME_DIR / "bin"

    # ------------ TELEGRAM ------------  
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None)
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None)
    PICKLEPERSISTENCE_DIR: Path = SETTINGS_DIR / "bot_data.pickle"
    CONNECT_TIMEOUT: int = 60
    READ_TIMEOUT: int = 60
    
    # ------------ YT-DLP ------------  
    YT_DLP_URL: str = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

    model_config = SettingsConfigDict(  
        env_file=get_env_paths(),  
        env_file_encoding="utf-8",  
        extra="ignore"  
    )

    def create_dirs(self) -> None:  
        """  
        Crea los directorios si no existen  
        """  
        dir_path = [
            self.HOME_DIR,
            self.SETTINGS_DIR,
            self.CACHE_DIR,
            self.LOGS_DIR,
            self.BIN_DIR
        ]
        for path in dir_path:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)