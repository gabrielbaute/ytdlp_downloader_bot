import logging  
from pathlib import Path  
from typing import Dict, Optional  
from logging.handlers import RotatingFileHandler

class FixedWidthFormatter(logging.Formatter):  
    """  
    Formateador que asegura un ancho fijo para el levelname.  
    """  
    def __init__(self, fmt=None, datefmt=None, level_width=8):  
        super().__init__(fmt, datefmt)  
        self.level_width = level_width  
      
    def format(self, record):  
        # Formateamos el levelname con ancho fijo y justificación izquierda  
        record.levelname = record.levelname.ljust(self.level_width)  
        return super().format(record)

class OctopusLogger:  
    """  
    Configuración del sistema de logs.  
    """  
    # Parámetros de rotación: 5MB por archivo, manteniendo hasta 5 backups  
    MAX_BYTES: int = 5 * 1024 * 1024   
    BACKUP_COUNT: int = 5  
    LEVEL_MAP: Dict[str, int] = {  
        "DEBUG": logging.DEBUG,  
        "INFO": logging.INFO,  
        "WARNING": logging.WARNING,  
        "ERROR": logging.ERROR,  
        "CRITICAL": logging.CRITICAL  
    }

    @staticmethod  
    def setup_logging(logs_dir: Path, level: Optional[str] = "INFO") -> None:  
        """  
        Configura el sistema de logging básico.

        Args:  
            logs_dir (Path): Directorio donde se guardarán los logs.  
            level (Optional[str]): Nivel de registro. Ejemplo: "DEBUG", "INFO", etc.

        Returns:  
            None  
        """  
        # Aseguramos que el directorio de logs existe  
        if not logs_dir.exists():  
            logs_dir.mkdir(parents=True, exist_ok=True)  
          
        log_file: Path = logs_dir / "botdownloader.log"

        # Definimos el formato base  
        log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"  
          
        # Handler de Rotación  
        rotate_handler = RotatingFileHandler(  
            filename=str(log_file),  
            mode="a",  
            maxBytes=OctopusLogger.MAX_BYTES,  
            backupCount=OctopusLogger.BACKUP_COUNT,  
            encoding="utf-8"  
        )

        # Handler de Consola  
        stream_handler = logging.StreamHandler()

        # Formateador con ancho fijo (8 caracteres, como Uvicorn)  
        formatter = FixedWidthFormatter(  
            fmt=log_format,  
            datefmt="%Y-%m-%d %H:%M:%S",  
            level_width=8  
        )  
          
        # Aplicamos el formateador a ambos handlers  
        rotate_handler.setFormatter(formatter)  
        stream_handler.setFormatter(formatter)

        # Configuramos el logger root  
        root_logger = logging.getLogger()  
        root_logger.setLevel(OctopusLogger.LEVEL_MAP.get(str(level), logging.INFO))  
          
        # Limpiamos handlers existentes para evitar duplicados  
        root_logger.handlers.clear()  
          
        # Agregamos handlers personalizados  
        root_logger.addHandler(rotate_handler)  
        root_logger.addHandler(stream_handler)