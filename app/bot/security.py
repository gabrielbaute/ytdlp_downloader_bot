from functools import wraps
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

def restricted(func: Callable) -> Callable:
    """
    Decorador que actúa como middleware de autorización.
    
    Args:
        func (Callable): Función original del bot (el callback).
        
    Returns:
        Callable: La función envuelta con validación de seguridad.
    """
    @wraps(func)
    async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # 1. Verificación de identidad
        is_admin = str(chat_id) == self.settings.TELEGRAM_CHAT_ID
        is_authorized = chat_id in context.bot_data.get("authorized_chats", {})

        if is_admin or is_authorized:
            return await func(self, update, context, *args, **kwargs)

        # 2. Si no está autorizado: Notificar al Admin
        self.logger.warning(f"Intento de acceso no autorizado: {user.first_name} ({chat_id})")
        
        # Enviamos notificación al administrador definido en .env
        await context.bot.send_message(
            chat_id=self.settings.TELEGRAM_CHAT_ID,
            text=(
                f"<b>🔔 Solicitud de Acceso</b>\n\n"
                f"<b>Nombre:</b> {user.first_name} {user.last_name or ''}\n"
                f"<b>Username:</b> @{user.username or 'N/A'}\n"
                f"<b>ID:</b> <code>{chat_id}</code>\n\n"
                f"Para autorizar, usa:\n<code>/authorize {chat_id}</code>"
            ),
            parse_mode="HTML"
        )

        # 3. Informar al usuario
        await update.message.reply_text("❌ No tienes acceso. Se ha enviado una solicitud al administrador.")
        return

    return wrapped