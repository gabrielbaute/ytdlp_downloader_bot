import asyncio
import re
import logging
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, Dict

from app.errors import BotError
from app.settings import Settings

class DownloaderService:
    """
    Wrapper de YT-DLP para la descarga del contenido.

    Uso:
        from app.services.downloader_service import DownloaderService
        from app.settings.load_settings import settings
        downloader = DownloaderService(settings)
    """
    def __init__(self, settings: Settings):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.progress_re = re.compile(r"\[download\]\s+(\d+\.\d+)%")

    async def download(
        self, 
        url: str, 
        only_audio: bool = False,
        progress_callback: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None
    ) -> Path:
        """
        Orquestador principal de la descarga.

        Args:
            url (str): Enlace del recurso.
            only_audio (bool): Determina si se extrae solo audio.
            progress_callback: Corutina para reporte de progreso.

        Returns:
            Path: Ruta al archivo descargado.

        Raises:
            BotError: Si falla la descarga o excede límites.
        """
        self.logger.info(f"📥 Descargando: {url}")
        args = self._build_args(url, only_audio)
        
        # Ejecución y consumo de salida
        downloaded_path_str = await self._run_yt_dlp(args, progress_callback)
        
        if not downloaded_path_str:
            raise BotError("No se pudo determinar la ruta del archivo descargado.")

        return self._validate_file(Path(downloaded_path_str))

    def _build_args(self, url: str, only_audio: bool) -> list[str]:
        """
        Construye los argumentos para el binario.

        Args:
            url (str): Enlace del recurso.
            only_audio (bool): Determina si se extrae solo audio.

        Returns:
            list[str]: Lista de argumentos para el binario. Nombre normalizado para Windows.
        """
        output_tmpl = str(self.settings.CACHE_DIR / "%(title)s.%(ext)s")
        bin_path = str(self.settings.BIN_DIR / "yt-dlp")
        
        args = [
            bin_path, 
            "--no-playlist", 
            "--newline",
            "--restrict-filenames",
            "--output", output_tmpl, 
            url
        ]
        
        if only_audio:
            args.extend(["-x", "--audio-format", "mp3"])
        else:
            args.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
        
        return args

    async def _run_yt_dlp(
        self, 
        args: list[str], 
        progress_callback: Optional[Callable]
    ) -> Optional[str]:
        """
        Maneja el ciclo de vida del subproceso.
        
        Args:
            args: Lista de argumentos para el binario.
            progress_callback: Corutina para reportar el progreso a la UI.

        Returns:
            Optional[str]: La ruta final del archivo en disco.
        """
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Consumimos la salida para obtener el progreso y el nombre del archivo
        file_path, _ = await asyncio.gather(
            self._consume_stdout(process.stdout, progress_callback),
            process.wait()
        )

        if process.returncode != 0:
            stderr_data = await process.stderr.read()
            self.logger.error(f"Error en yt-dlp: {stderr_data.decode()}")
            raise BotError("Error en yt-dlp", details={"stderr": stderr_data.decode()})

        self.logger.info(f"✅ Archivo descargado: {file_path}")
        return file_path

    async def _consume_stdout(
        self, 
        stdout: asyncio.StreamReader, 
        callback: Optional[Callable]
    ) -> Optional[str]:
        """
        Procesa el flujo de salida en tiempo real.

        Args:
            stdout: Flujo de salida del subproceso.
            callback: Corutina para reportar el progreso a la UI.

        Returns:
            Optional[str]: La ruta final del archivo en disco.
        """
        found_path = None

        while True:
            line_bytes = await stdout.readline()
            if not line_bytes:
                break
            
            # 0. Leemos el stream de bytes desde la consola con manejo de errores para Windows
            try:
                line = line_bytes.decode("utf-8", errors="replace").strip()
            except Exception:
                # Fallback extremo por si acaso
                line = line_bytes.decode("latin-1", errors="replace").strip()            
            
            # 1. Extraer porcentaje de progreso
            if callback and (match := self.progress_re.search(line)):
                await callback(f"{match.group(1)}%")

            # 2. Capturar ruta (Estrategia multilínea)
            
            # Caso A: Destino inicial o archivo ya descargado (Captura .webm o .m4a temporales)
            if "[download] Destination:" in line:
                found_path = line.split("Destination: ")[1].strip()
            elif "has already been downloaded" in line:
                found_path = line.split("[download] ")[1].split(" has already")[0].strip()
            
            # Caso B: Importante para Videos. 
            # Cuando hay merge de video+audio, actualizamos a la ruta del .mp4 final.
            elif "[Merger] Merging formats into" in line:
                # Ejemplo: [Merger] Merging formats into "cache/video.mp4"
                path_match = re.search(r'into "(.+)"', line)
                if path_match:
                    found_path = path_match.group(1)
            
            # Caso C: Importante para Audios (NUEVO)
            # Tras la conversión de FFmpeg a MP3, yt-dlp indica el archivo definitivo aquí.
            elif "[ExtractAudio] Destination:" in line:
                # Ejemplo: [ExtractAudio] Destination: cache/musica.mp3
                found_path = line.split("Destination: ")[1].strip()

            # Caso D: Si no hubo merge/extracción pero terminó la descarga
            elif "[download] 100% of" in line and "in" in line:
                # Mantenemos esta sección por si el flujo no entra en Merger o ExtractAudio
                pass
                
        return found_path

    def _validate_file(self, file_path: Path) -> Path:
        """
        Valida que el archivo no supere el tamaño permitido por Telegram para el envío de arvhivos.

        Args:
            file_path (Path): Ruta al archivo.

        Returns:
            Path: Ruta al archivo.
            
        Raises:
            BotError: Si el archivo excede el límite.
        """
        if not file_path.exists():
            raise BotError(f"El archivo no existe en la ruta: {file_path}")

        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > 50:
            file_path.unlink(missing_ok=True) # Uso de pathlib para borrar
            raise BotError(
                f"El archivo ({file_size_mb:.1f}MB) excede el límite de 50MB.",
                details={"size": file_size_mb}
            )
            
        return file_path