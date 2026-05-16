import os
import sys
import logging
import pystray
import threading
import subprocess
import tkinter as tk
from PIL import Image
from tkinter import messagebox

from app.bot.downloader_bot import DownloaderBot
from app.settings import settings, OctopusLogger, SettingsGUI, get_resource_path


class BotTrayApp:
    def __init__(self):
        self.bot_instance = None
        self.bot_thread = None
        self.icon = None
        
        # Configuración de Logs
        OctopusLogger.setup_logging(logs_dir=settings.LOGS_DIR, level="INFO")
        self.logger = logging.getLogger("TrayApp")
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        # Inicializamos Tkinter oculto para diálogos y ventanas
        self.root = tk.Tk()
        self.root.withdraw()
        
        self._create_tray()

    def _get_icon_image(self):
        icon_path = get_resource_path("assets/logo_250.png")
        if icon_path.exists():
            return Image.open(icon_path).resize((64, 64))
        return Image.new('RGB', (64, 64), color=(31, 118, 180))

    def open_logs(self):
        """Abre el archivo de logs con el editor predeterminado del sistema."""
        log_file = settings.LOGS_DIR / "octopus_music.log"
        if log_file.exists():
            if sys.platform == "win32":
                os.startfile(log_file)
            else:
                
                subprocess.run(["xdg-open", str(log_file)])
        else:
            messagebox.showinfo("Logs", "El archivo de logs aún no ha sido creado.")

    def open_settings(self):
        """
        Lanza la interfaz de configuración en un hilo independiente.
        """
        self.logger.info("Abriendo panel de configuración...")
        
        def launch_gui():
            # Creamos la GUI con su propio root independiente
            gui = SettingsGUI(settings)
            gui.run()

        # Al usar un hilo nuevo con su propio tk.Tk(), la ventana se dibujará
        # sin importar que el Tray esté ocupado.
        threading.Thread(target=launch_gui, daemon=True).start()

    def start_bot(self):
        if not settings.TELEGRAM_BOT_TOKEN or "INSERTAR" in settings.TELEGRAM_BOT_TOKEN:
            messagebox.showwarning("Falta Configuración", "Por favor, configura el Token antes de iniciar.")
            self.open_settings()
            return

        if self.bot_thread and self.bot_thread.is_alive():
            return
            
        self.bot_thread = threading.Thread(target=self._run_bot_logic, daemon=True)
        self.bot_thread.start()
        self.icon.notify("Bot iniciado", title="DownloaderBot")

    def _run_bot_logic(self):
        try:
            self.bot_instance = DownloaderBot(settings=settings)
            self.bot_instance.run()
        except Exception as e:
            self.logger.error(f"Error en ejecución: {e}")

    def stop_bot(self):
        """Detiene el bot usando el nuevo método no bloqueante."""
        if self.bot_instance:
            self.icon.notify("Deteniendo servicios...", title="DownloaderBot")
            # Ejecutamos el stop en un hilo para que el menú del tray no se congele
            self.bot_instance.stop()

    def quit_app(self, icon):
        self.logger.info("Cerrando aplicación completa...")
        self.stop_bot()
        icon.stop()
        # No usamos sys.exit aquí para evitar el traceback del manejador
        self.root.after(0, self.root.destroy)

    def _create_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Iniciar Bot", self.start_bot),
            pystray.MenuItem("Detener Bot", self.stop_bot),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Configuración", self.open_settings),
            pystray.MenuItem("Ver Logs", self.open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self.quit_app)
        )
        
        self.icon = pystray.Icon(
            "BotDownloader", 
            self._get_icon_image(), 
            f"BotDownloader v{settings.APP_VERSION}", 
            menu
        )

    def run(self):
        self.logger.info("Ejecutando Tray...")
        self.icon.run()

if __name__ == "__main__":
    app = BotTrayApp()
    app.run()