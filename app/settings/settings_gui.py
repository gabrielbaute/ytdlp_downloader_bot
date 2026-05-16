import logging
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import ttk, messagebox

from app.settings.app_bootstrap import AppBootstrap
from app.settings.app_settings import Settings
from app.settings.resource_path import get_resource_path

class SettingsGUI:
    """
    Interfaz gráfica modular para la configuración del bot.
    """
    def __init__(self, settings: Settings):
        """
        Args:
            settings: Instancia de configuración de la app.
        """
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self.root = tk.Tk()
        self.root.title(f"Configuración - {self.settings.APP_NAME}")
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        
        # Mantener al frente
        self.root.attributes("-topmost", True)
        
        # Contenedor principal con padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill="both", expand=True)
        
        self._set_icon()
        self._setup_ui()
    
    def _set_icon(self) -> None:
        """
        Carga el logo y lo establece como icono de la ventana.
        """
        try:
            icon_path = get_resource_path("assets/logo_250.png")
            if icon_path.exists():
                img = Image.open(icon_path)
                # Redimensionamos para el icono de la barra de título (típicamente 32x32)
                img_icon = ImageTk.PhotoImage(img.resize((32, 32)))
                self.root.iconphoto(True, img_icon)
                # Guardamos referencia para que el GC no la borre
                self._icon_ref = img_icon 
        except Exception as e:
            self.logger.error(f"No se pudo cargar el icono: {e}")

    def _setup_ui(self) -> None:
        """
        Define la estructura visual del formulario.
        """
        tg_frame = ttk.LabelFrame(self.main_frame, text=" Credenciales de Telegram ", padding="10")
        tg_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(tg_frame, text="Bot Token:").pack(fill="x")
        self.token_entry = ttk.Entry(tg_frame)
        self.token_entry.insert(0, getattr(self.settings, "TELEGRAM_BOT_TOKEN", ""))
        self.token_entry.pack(pady=(2, 10), fill="x")

        ttk.Label(tg_frame, text="Admin Chat ID:").pack(fill="x")
        self.chat_id_entry = ttk.Entry(tg_frame)
        self.chat_id_entry.insert(0, getattr(self.settings, "TELEGRAM_CHAT_ID", ""))
        self.chat_id_entry.pack(pady=(2, 5), fill="x")

        conn_frame = ttk.LabelFrame(self.main_frame, text=" Parámetros de Conexión ", padding="10")
        conn_frame.pack(fill="x", pady=(0, 20))

        # Usamos un Frame interno para poner los timeouts lado a lado
        timeout_inner = ttk.Frame(conn_frame)
        timeout_inner.pack(fill="x")

        # Connect Timeout
        c_sub_frame = ttk.Frame(timeout_inner)
        c_sub_frame.pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Label(c_sub_frame, text="Connect (s):").pack(anchor="w")
        self.conn_timeout_entry = ttk.Entry(c_sub_frame)
        # Usamos valor por defecto 60 si no existe
        self.conn_timeout_entry.insert(0, str(getattr(self.settings, "CONNECT_TIMEOUT", 60)))
        self.conn_timeout_entry.pack(fill="x")

        # Read Timeout
        r_sub_frame = ttk.Frame(timeout_inner)
        r_sub_frame.pack(side="left", expand=True, fill="x", padx=(5, 0))
        ttk.Label(r_sub_frame, text="Read (s):").pack(anchor="w")
        self.read_timeout_entry = ttk.Entry(r_sub_frame)
        self.read_timeout_entry.insert(0, str(getattr(self.settings, "READ_TIMEOUT", 60)))
        self.read_timeout_entry.pack(fill="x")

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", side="bottom")

        ttk.Button(
            btn_frame, 
            text="Guardar Configuración", 
            command=self._save,
            style="Accent.TButton" # Por si decides añadir un tema más adelante
        ).pack(side="right", padx=5)

    def _save(self) -> None:
        """
        Recopila los datos, valida tipos y guarda mediante AppBootstrap.
        """
        data = {
            "token": self.token_entry.get().strip(),
            "chat_id": self.chat_id_entry.get().strip(),
            "conn_t": self.conn_timeout_entry.get().strip(),
            "read_t": self.read_timeout_entry.get().strip()
        }

        # Validación básica de vacíos
        if not all(data.values()):
            self.logger.warning("Campos incompletos en la configuración.")
            messagebox.showwarning("Campos incompletos", "Por favor, rellena todos los campos.")
            return

        try:
            bootstrap = AppBootstrap(self.settings)
            bootstrap.write_config(
                token=data["token"], 
                chat_id=data["chat_id"],
                connect_timeout=int(data["conn_t"]),
                read_timeout=int(data["read_t"])
            )
            # Agregamos parent=self.root para evitar conflictos de hilos en diálogos
            messagebox.showinfo("Éxito", "Configuración guardada.", parent=self.root)
            self.root.destroy()
        except ValueError as e:
            self.logger.error(f"Valor inválido: {e}")
            messagebox.showerror("Error", f"Valor inválido: {e}", parent=self.root)
        except Exception as e:
            self.logger.error(f"No se pudo guardar: {e}")
            messagebox.showerror("Error", f"No se pudo guardar: {e}", parent=self.root)

    def run(self):
        """Inicia el mainloop de la ventana."""
        self.root.mainloop()