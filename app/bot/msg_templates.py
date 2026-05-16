from typing import Optional, Any

class DownloaderBotMessages:
    """
    Set de mensajes para el bot.
    """
    def __init__(self):
        pass
    
    @staticmethod
    def pick_message(key: str, args: Optional[Any] = None) -> str:
        """
        Devuelve un mensaje personalizado por comando.
        """
        templates = {
                "admin_notification_error": "❌ <b>Error:</b>\n\n {error_details}",
                "admin_notification_warning": "⚠️ <b>Advertencia:</b>\n\n {warning_details}",
                "error_usage_authorize": "❌ Uso: /authorize <chat_id>",
                "start_success": "<b>🚀 Sistema Operativo</b>\nHola {name}, envía un link.",
                "ytdlp_ok": "✅ <b>yt-dlp</b> está instalado correctamente.",
                "ytdlp_fail": "❌ <b>Error:</b> No se encontró el binario.\nUsa /install.",
                "ytdlp_version": "<b>yt-dlp</b> versión: {version}",
                "installing": "⏳ Iniciando instalación de yt-dlp...",
                "unauthorized": "🚫 Acceso denegado para el ID: {id}"
            }
        if args:
            return templates[key].format(**args)
        else:
            return templates[key]