import sys
from typing import Tuple
from pathlib import Path

def get_env_paths() -> Tuple[Path, ...]:
    """
    Retorna una jerarquía de rutas donde buscar el archivo .env.
    """        
    user_path = Path.home() / ".botdownloader" / "settings" / ".env"
    local_path = Path(__file__).resolve().parent.parent.parent / ".env"
    
    if getattr(sys, 'frozen', False):
        return (user_path,)
    
    return (user_path, local_path)