"""
Módulo para gestionar la instalación/actualización del binario de yt-dlp.
"""
import os
import sys
import stat
import logging
import platform
import urllib.request
from pathlib import Path
from typing import Optional

from app.errors import YTDLPError
from app.settings.app_settings import Settings

class YTDLPInstaller:
    """
    Clase para gestionar la instalación y actualización del binario yt-dlp.
    
    Uso:
        from app.services.ytdlp_installer import YTDLPInstaller
        from app.settings.load_settings import settings
        installer = YTDLPInstaller(settings)
        installer.install()  # Descarga si no existe
        installer.ensure_installed()  # Verifica y descarga si es necesario
    """
    
    def __init__(self, settings: Settings):
        """
        Inicializa el instalador.
        
        Args:
            settings: Instancia singleton de Settings
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.bin_name = self._get_binary_name()
        self.bin_path = settings.BIN_DIR / self.bin_name
        
        # Asegurar que el directorio BIN_DIR existe
        self.settings.BIN_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_binary_name(self) -> str:
        """
        Retorna el nombre del binario según el SO.
        
        Returns:
            str: Nombre del binario requerido para el sistema operativo.
        """
        system = platform.system().lower()
        if system == "windows":
            return "yt-dlp.exe"
        elif system == "darwin":  # macOS
            return "yt-dlp"
        else:  # Linux y otros Unix-like
            return "yt-dlp"

    def _get_binary_url(self) -> str:
        """
        Retorna la URL de descarga correcta según el SO.
        """
        system = platform.system().lower()
        base_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"
        
        if system == "windows":
            return f"{base_url}yt-dlp.exe"
        # Linux y macOS suelen usar el mismo binario (el que ya tienes)
        return f"{base_url}yt-dlp"

    def _download_binary(self) -> None:
        """
        Descarga el binario de yt-dlp desde la URL de sistema.
        """
        # Obtenemos la URL correcta dinámicamente
        target_url = self._get_binary_url()
        
        self.logger.info(f"📥 Descargando yt-dlp desde {target_url}")
        self.logger.info(f"📍 Destino: {self.bin_path}")
        
        # urllib.request.urlretrieve funciona bien para descargar el .exe
        urllib.request.urlretrieve(target_url, self.bin_path)
        
        # En Linux/Mac, dar permisos de ejecución (usando pathlib para coherencia)
        if platform.system().lower() != "windows":
            import stat
            self.bin_path.chmod(self.bin_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self.logger.info(f"🔐 Permisos de ejecución asignados")

    def is_installed(self) -> bool:
        """
        Verifica si el binario ya existe y es ejecutable.
        
        Returns:
            bool: True si el binario existe y tiene permisos de ejecución (en Unix)
        """
        if not self.bin_path.exists():
            return False
        
        # En Windows, no necesitamos verificar permisos de ejecución
        if platform.system().lower() == "windows":
            return True
        
        # En Unix, verificar que sea ejecutable
        return os.access(self.bin_path, os.X_OK)

    def install(self, force: bool = False) -> Path:
        """
        Ejecuta la descarga e instalación del binario.
        
        Args:
            force: Si es True, fuerza la reinstalación aunque ya exista.
        
        Returns:
            Path: Ruta al binario instalado.
            
        Raises:
            Exception: Si ocurre un error durante la instalación.
        """
        if not force and self.is_installed():
            self.logger.info(f"✅ Binario ya existe en: {self.bin_path}")
            return self.bin_path
        
        try:
            self._download_binary()
            self.logger.info(f"✅ Binario instalado correctamente: {self.bin_path}")
            return self.bin_path
            
        except urllib.error.URLError as e:
            self.logger.error(f"❌ Error de red al descargar: {e}")
            raise Exception(f"No se pudo descargar yt-dlp: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error instalando yt-dlp: {e}")
            raise
    
    def ensure_installed(self) -> Path:
        """
        Verifica que el binario esté instalado, si no lo está, lo instala. Usar al inicio de la instalación.
        
        Returns:
            Path: Ruta al binario.
        """
        if not self.is_installed():
            self.logger.warning("⚠️ yt-dlp no encontrado. Comenzando instalación...")
            return self.install()
        
        self.logger.info(f"✅ yt-dlp ya está instalado en: {self.bin_path}")
        return self.bin_path
    
    def get_version(self) -> Optional[str]:
        """
        Obtiene la versión del binario instalado.
        
        Returns:
            Optional[str]: Versión de yt-dlp o None si no está instalado.
        """
        if not self.is_installed():
            return None
        
        import subprocess
        try:
            result = subprocess.run(
                [str(self.bin_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.error(f"Error obteniendo versión: {e}")
            raise YTDLPError(
                message=f"Error obteniendo versión: {e}",
                details={"command": " ".join([str(self.bin_path), "--version"])}
            )
        
        return None