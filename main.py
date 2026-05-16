import io
import sys
import logging

from app.settings import settings, OctopusLogger
from app.bot.downloader_bot import DownloaderBot

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OctopusLogger.setup_logging(logs_dir=settings.LOGS_DIR, level="INFO")

def main() -> None:
    """
    Punto de entrada principal para inicializar y ejecutar el bot.
    """
    # 1. Configuración de logs
    logger = logging.getLogger("Main")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    try:
        # 2. Instanciar el Bot
        # DownloaderBot ya recibe settings e instancia sus servicios internamente
        bot = DownloaderBot(settings=settings)

        # 3. Ejecutar
        logger.info("Iniciando el ciclo de vida del bot...")
        bot.run()

    except KeyboardInterrupt:
        logger.info("Deteniendo el bot...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Error fatal al arrancar el bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()