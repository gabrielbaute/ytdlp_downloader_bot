import sys
import logging
from pathlib import Path
from app.settings.app_settings import Settings

class AppBootstrap:
    """
    Gestor de inicialización para entornos locales (Binario).
    Crea la estructura de carpetas y el archivo .env inicial si no existen.
    """
    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings (Settings): Instancia de configuración.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.user_env_path: Path = settings.SETTINGS_DIR / ".env"

    def _get_template(self, token: str, chat_id: str, conn_t: int = 60, read_t: int = 60) -> str:
        """
        Genera el contenido base para el archivo .env.
        """
        return (
            "# BotDownloader Settings\n"
            f"TELEGRAM_BOT_TOKEN={token}\n"
            f"TELEGRAM_CHAT_ID={chat_id}\n"
            f"CONNECT_TIMEOUT={conn_t}\n"
            f"READ_TIMEOUT={read_t}\n"
        )

    def write_config(self, token: str, chat_id: str, connect_timeout: int = 60, read_timeout: int = 60) -> None:
        """
        Escribe físicamente el archivo .env en la carpeta de configuración del usuario.
        """
        try:
            # Aseguramos que el directorio exista antes de escribir
            self.settings.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            
            content = self._get_template(token, chat_id, connect_timeout, read_timeout)
            self.user_env_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Archivo de configuración creado/actualizado en: {self.user_env_path}")
        except Exception as e:
            self.logger.error(f"Error al escribir el archivo .env: {e}")
            raise

    def create_env_if_missing(self) -> None:
        """
        Crea el entorno inicial si el archivo .env no existe.
        Solo se usará para la primera ejecución del binario.
        """
        if self.user_env_path.exists():
            self.logger.info("El entorno ya está inicializado.")
            return

        self.logger.info("Primer arranque detectado. Creando entorno de usuario...")
        
        # Tomamos lo que haya en settings (placeholders o vacíos) para el primer .env
        token = self.settings.TELEGRAM_BOT_TOKEN or "INSERTAR_BOT_TOKEN"
        chat_id = self.settings.TELEGRAM_CHAT_ID or "0"
        
        try:
            # Crear todos los directorios necesarios definidos en settings
            self.settings.HOME_DIR.mkdir(parents=True, exist_ok=True)
            self.settings.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            self.settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self.settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            self.settings.BIN_DIR.mkdir(parents=True, exist_ok=True)
            
            # Escribir el archivo .env inicial
            self.write_config(token, chat_id)
            
        except Exception as e:
            self.logger.error(f"Fallo crítico al crear el entorno de usuario: {e}")
            sys.exit(1)