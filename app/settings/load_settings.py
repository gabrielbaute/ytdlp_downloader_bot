import sys
from app.settings.app_settings import Settings

def load_settings() -> Settings:
    """
    Crea una instancia única de settings e inicializa el bootstrap
    """
    settings = Settings()
    settings.create_dirs()

    # SOLO ejecutamos el bootstrap si es un binario (Nuitka/PyInstaller)
    if getattr(sys, 'frozen', False):
        from app.settings.app_bootstrap import AppBootstrap
        bootstrap = AppBootstrap(settings)
        bootstrap.create_env_if_missing()
        
        # Opcional: Recargar settings si el bootstrap creó el archivo por primera vez
        settings = Settings() 

    return settings

settings = load_settings()