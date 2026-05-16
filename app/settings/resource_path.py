import sys
import os
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """
    Obtiene la ruta absoluta de un recurso para desarrollo o ejecutable.
    """
    base_path = Path(getattr(sys, '_MEIPASS', os.path.abspath(".")))
    return base_path / relative_path