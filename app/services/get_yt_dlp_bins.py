"""Módulo para gestionar la instalación/actualización del binario de yt-dlp."""
import os
import json
import logging
import platform
import urllib.request
from pathlib import Path
from typing import Optional

from app.settings.app_settings import Settings
from app.errors import BinNotFoundError, YTDLPError

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
        """Inicializa el instalador.

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
        """Retorna el nombre del binario según el SO.

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
        """Retorna la URL de descarga correcta según el SO."""
        system = platform.system().lower()
        base_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"

        if system == "windows":
            return f"{base_url}yt-dlp.exe"
        return f"{base_url}yt-dlp"

    def _download_binary(self) -> None:
        """Descarga el binario de yt-dlp desde la URL de sistema."""
        target_url = self._get_binary_url()

        self.logger.info(f"📥 Descargando yt-dlp desde {target_url}")
        self.logger.info(f"📍 Destino: {self.bin_path}")

        urllib.request.urlretrieve(target_url, self.bin_path)

        if platform.system().lower() != "windows":
            import stat

            self.bin_path.chmod(
                self.bin_path.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )
            self.logger.info("🔐 Permisos de ejecución asignados")

    def is_installed(self) -> bool:
        """Verifica si el binario ya existe y es ejecutable.

        Returns:
            bool: True si el binario existe y tiene permisos de ejecución (en Unix)
        """
        if not self.bin_path.exists():
            return False

        if platform.system().lower() == "windows":
            return True

        return os.access(self.bin_path, os.X_OK)

    def install(self, force: bool = False) -> Path:
        """Ejecuta la descarga e instalación del binario.

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
            self.logger.info(
                f"✅ Binario instalado correctamente: {self.bin_path}"
            )
            return self.bin_path

        except urllib.error.URLError as e:
            self.logger.error(f"❌ Error de red al descargar: {e}")
            raise Exception(f"No se pudo descargar yt-dlp: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error instalando yt-dlp: {e}")
            raise

    def ensure_installed(self) -> Path:
        """Verifica que el binario esté instalado, si no lo está, lo instala.

        Usar al inicio de la instalación.

        Returns:
            Path: Ruta al binario.
        """
        if not self.is_installed():
            self.logger.warning(
                "⚠️ yt-dlp no encontrado. Comenzando instalación..."
            )
            return self.install()

        self.logger.info(f"✅ yt-dlp ya está instalado en: {self.bin_path}")
        return self.bin_path

    def get_version(self) -> Optional[str]:
        """Obtiene la versión del binario instalado.

        Returns:
            Optional[str]: Versión de yt-dlp o None si no está instalado.

        Raises:
            YTDLPError: Si el subproceso falla al consultar la versión.
        """
        if not self.is_installed():
            return None

        import subprocess

        try:
            result = subprocess.run(
                [str(self.bin_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.error(f"Error obteniendo versión: {e}")
            raise YTDLPError(
                message=f"Error obteniendo versión: {e}",
                details={
                    "command": " ".join([str(self.bin_path), "--version"])
                },
            )

        return None

    def update_yt_dlp(self) -> bool:
        """Comprueba y actualiza el binario de yt-dlp a la última versión.

        Compara el tag remoto estable de la API de GitHub contra la versión del
        ejecutable local actual. Si difieren, invoca la reinstalación forzada.

        Returns:
            bool: True si el binario se actualizó con éxito. False si ya se
                encontraba en la versión más reciente.

        Raises:
            BinNotFoundError: Si se intenta actualizar pero yt-dlp no está instalado.
            YTDLPError: Si falla la consulta remota, el procesamiento de la API o
                la ejecución/reinstalación del subproceso binario.
        """
        if not self.is_installed():
            self.logger.warning(
                "⚠️ yt-dlp no encontrado. No se puede actualizar."
            )
            raise BinNotFoundError(
                message="No se puede actualizar un binario no instalado.",
                details={"bin_path": str(self.bin_path)},
            )

        self.logger.info("🔄 Comprobando actualizaciones para yt-dlp...")

        # 1. Obtener versión local
        current_version: Optional[str] = self.get_version()
        if not current_version:
            raise YTDLPError(
                message="El binario existe pero no devolvió una versión válida.",
                details={"bin_path": str(self.bin_path)},
            )

        current_version = current_version.strip()
        self.logger.info(f"📦 Versión local instalada: {current_version}")

        # 2. Consultar versión remota en GitHub
        api_url: str = (
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        )
        req = urllib.request.Request(
            api_url, headers={"User-Agent": "BotDownloader-Update-Service"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status != 200:
                    raise YTDLPError(
                        message="Error al conectar con la API de GitHub.",
                        details={"status_code": response.status},
                    )

                data = json.loads(response.read().decode())
                latest_version: str = data.get("tag_name", "").strip()

            if not latest_version:
                raise YTDLPError(
                    message="La API de GitHub devolvió una estructura sin tag_name."
                )

            self.logger.info(
                f"🌐 Última versión disponible en GitHub: {latest_version}"
            )

            # 3. Normalizar y comparar versiones
            normalized_local: str = current_version.lower().removeprefix("v")
            normalized_latest: str = latest_version.lower().removeprefix("v")

            if normalized_local == normalized_latest:
                self.logger.info(
                    "✅ yt-dlp ya está en su versión más reciente."
                )
                return False

            # 4. Forzar instalación/actualización
            self.logger.info(
                f"🚀 Versión desactualizada. Actualizando a [{latest_version}]..."
            )

            # install() retorna un Path si todo sale bien, o levanta una excepción genérica
            self.install(force=True)

            # Validar que la nueva versión se vea reflejada correctamente
            updated_version: Optional[str] = self.get_version()
            self.logger.info(
                f"🎉 yt-dlp actualizado con éxito a la versión: {updated_version}"
            )
            return True

        except urllib.error.URLError as e:
            self.logger.error(f"❌ Error de red comprobando actualización: {e}")
            raise YTDLPError(
                message=f"Fallo de conexión al verificar actualización de yt-dlp: {e.reason}",
                details={"url": api_url},
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Error decodificando respuesta JSON: {e}")
            raise YTDLPError(
                message="La respuesta de GitHub no pudo ser parseada como JSON.",
                details={"exception": str(e)},
            )
        except Exception as e:
            self.logger.error(
                f"❌ Error inesperado actualizando el binario: {e}"
            )
            raise YTDLPError(
                message=f"Fallo crítico en el proceso de actualización: {str(e)}",
                details={"bin_path": str(self.bin_path)},
            )