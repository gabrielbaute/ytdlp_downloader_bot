import logging
import asyncio
import threading
from pathlib import Path
from typing import Optional, Any
from telegram.error import TelegramError
from telegram.request import HTTPXRequest
from telegram import Update, BotCommand, BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, PicklePersistence, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

from app.schemas import ChatID
from app.settings import Settings
from app.enums import DownloadType
from app.bot.security import restricted
from app.bot.msg_templates import DownloaderBotMessages
from app.services import YTDLPInstaller, DownloaderService
from app.errors import BotError, BinNotFoundError, YTDLPError

class DownloaderBot:
    def __init__(self, settings: Settings):
        """
        Bot de descargas sobre yt-dlp

        Args:
            settings (Settings): Configuración del bot.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self._loop = None
        self.stop_event = None
        self.ytdlp_installer = YTDLPInstaller(settings)
        self.downloader_service = DownloaderService(settings)
        self.persistence = PicklePersistence(filepath=settings.PICKLEPERSISTENCE_DIR)
        self.t_request = HTTPXRequest(connect_timeout=20, read_timeout=20)
        self.app = (
            Application.builder()
            .token(self.settings.TELEGRAM_BOT_TOKEN)
            .persistence(self.persistence)
            .request(self.t_request)
            .post_init(self.post_init)
            .build()
        )
        self._register_handlers()

    async def post_init(self, application: Application) -> None:
        """
        Configuración que se ejecuta al arrancar el bot.

        Args:
            application (Application): Instancia de la aplicación de Telegram.
        """
        # 0. Capturamos el hilo
        self._loop = asyncio.get_running_loop()
        # 1. Comandos para todo el mundo (Públicos)
        public_commands = [
            BotCommand("start", "Iniciar el bot y solicitar acceso")
        ]
        await application.bot.set_my_commands(public_commands)

        # 2. Comandos exclusivos para el Admin (Privados)
        admin_commands = [
            BotCommand("start", "Panel de control"),
            BotCommand("authorize", "Autorizar un ID de Telegram"),
            BotCommand("status", "Estado de los binarios"),
            BotCommand("install", "Instalar/Actualizar yt-dlp"),
            BotCommand("update", "Actualiza yt-dlp a la última versión estable"),
            BotCommand("revoke", "Revoca la autorización de un chat (Solo Admin)"), #TODO
        ]
        await self.app.bot.set_my_commands(
            admin_commands, 
            scope=BotCommandScopeChat(chat_id=int(self.settings.TELEGRAM_CHAT_ID))
        )
        self.logger.info("✅ Menús de comandos configurados dinámicamente")

    def _register_handlers(self) -> None:
        """
        Asocia los comandos con sus respectivos métodos.
        """
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("authorize", self.authorize_user))
        self.app.add_handler(CommandHandler("status", self.check_ytdlp_bins))
        self.app.add_handler(CommandHandler("check_version", self.check_ytdlp_version))
        self.app.add_handler(CommandHandler("install", self.install_ytdlp))
        self.app.add_handler(CommandHandler("update", self.update_ytdlp))
        self.app.add_handler(CommandHandler("stop", self.stop))
        
        # IMPORTANTE: Los botones se capturan con CallbackQueryHandler
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Captura de URLs (Texto que no sea comando)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        
        # Manejador de errores
        self.app.add_error_handler(self.error_handler)

        self.logger.info("✅ Handlers configurados")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        self.logger.error("Error procesando update:", exc_info=context.error)
        
        # Si es un error de Timeout, podemos simplemente ignorarlo o avisar al admin
        if isinstance(context.error, TelegramError):
             self.logger.warning(f"Error de red/API de Telegram: {context.error}")

    async def _send_ui_msg(
        self, 
        template_key: str, 
        update: Optional[Update] = None, 
        chat_id: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        Envía un mensaje basado en plantillas.
        
        Args:
            template_key: Clave del diccionario de mensajes.
            update: Objeto Update para extraer el chat_id dinámicamente.
            chat_id: ID explícito (prioritario o para alertas admin).
            **kwargs: Variables para rellenar la plantilla.
        """
        # 1. Selección del mensaje
        message_text = DownloaderBotMessages.pick_message(template_key, kwargs)

        # 2. Determinar destino
        target = chat_id or (update.effective_chat.id if update else int(self.settings.TELEGRAM_CHAT_ID))

        try:
            await self.app.bot.send_message(
                chat_id=target,
                text=message_text,
                parse_mode="HTML"
            )
        except Exception as e:
            self.logger.error(f"Error enviando mensaje ({template_key}): {e}")

    async def _send_downloaded_file(
        self, 
        update: Update, 
        file_path: Path, 
        is_audio: bool
    ) -> None:
        """
        Envía el archivo descargado al usuario y limpia la caché.

        Args:
            update: Objeto Update para obtener el chat_id.
            file_path: Ruta del archivo en disco (Pathlib).
            is_audio: Booleano que indica el tipo de contenido.
        """
        chat_id = update.effective_chat.id

        try:
            # Abrimos el archivo en modo lectura binaria (rb)
            with file_path.open("rb") as f:
                if is_audio:
                    # Lógica para envío de AUDIO
                    # Telegram lo procesa para que aparezca en el reproductor de música
                    await self.app.bot.send_audio(
                        chat_id=chat_id,
                        audio=f,
                        caption="🎵 Aquí tienes tu audio solicitado."
                    )
                else:
                    # Lógica para envío de VIDEO
                    # Telegram habilita el streaming (ver mientras se descarga)
                    await self.app.bot.send_video(
                        chat_id=chat_id,
                        video=f,
                        caption="🎬 Aquí tienes tu video solicitado.",
                        supports_streaming=True
                    )
            
            self.logger.info(f"✅ Archivo enviado exitosamente: {file_path.name}")

        except TelegramError as e:
            self.logger.error(f"Error de Telegram al enviar archivo: {e}")
            # Notificamos al admin si algo falla en el transporte
            await self._send_ui_msg(
                "admin_notification_error", 
                chat_id=int(self.settings.TELEGRAM_CHAT_ID),
                error_details=f"Fallo envío: {str(e)}"
            )
        
        finally:
            # REGLA DE ORO: Limpiar siempre el archivo después del intento de envío
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"🗑️ Caché limpiada: {file_path.name}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Callback interactivo para la selección de formato.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        query = update.callback_query
        await query.answer()

        url = context.user_data.get("current_url")
        if not url:
            await query.edit_message_text("⚠️ Sesión expirada. Por favor, envía el link de nuevo.")
            return

        # Variable para controlar la frecuencia de actualización
        last_notified_percent = -1.0

        async def progress_wrapper(percent_str: str) -> None:
            """Callback interno para throttling de UI."""
            nonlocal last_notified_percent
            try:
                current_percent = float(percent_str.replace('%', ''))
                # Actualizar solo si subió más de un 5% para evitar spam al API
                if current_percent >= last_notified_percent + 5.0:
                    await query.edit_message_text(f"⏳ Descargando: {percent_str}")
                    last_notified_percent = current_percent
            except Exception:
                pass

        try:
            is_audio = (query.data == DownloadType.DL_AUDIO)
                        
            file_path = await self.downloader_service.download(
                url=url,
                only_audio=is_audio,
                progress_callback=progress_wrapper
            )

            # Informamos al usuario antes de iniciar el upload
            await query.edit_message_text("📦 Archivo listo. Enviando a Telegram...")
            
            # INVOCACIÓN DEL NUEVO MÉTODO
            await self._send_downloaded_file(update, file_path, is_audio)
            
            # Opcional: Borrar el mensaje de "Enviando..." para limpiar el chat
            #await query.delete_message()
            
        except BotError as e:
            await query.edit_message_text(f"❌ {e.message}")
        except Exception as e:
            self.logger.error(f"Fallo sistémico: {e}")
            await query.edit_message_text("❌ Ocurrió un error inesperado.")
        finally:
            context.user_data.pop("current_url", None)

    @restricted
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Solo usuarios autorizados ven esto.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        await self._send_ui_msg(
            "start_success", 
            update=update, 
            name=update.effective_user.first_name
        )

    async def authorize_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Autoriza un ID de Telegram para el uso del bot. Comando exclusivo para el Admin.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        if str(update.effective_chat.id) != self.settings.TELEGRAM_CHAT_ID:
            return

        if not context.args:
            # Podrías añadir una plantilla "error_usage_authorize" en tu clase de mensajes
            await self._send_ui_msg("error_usage_authorize", update=update)
            return

        try:
            target_id = int(context.args[0])
            
            new_chat_data = ChatID(
                chat_id=target_id,
                first_name="Pendiente de inicio",
                username="N/A"
            )

            if "authorized_chats" not in context.bot_data:
                context.bot_data["authorized_chats"] = {}

            context.bot_data["authorized_chats"][target_id] = new_chat_data.model_dump()
            await self.app.persistence.flush() 
            
            # Notificación al admin (confirmación)
            await self._send_ui_msg(
                "admin_notification_warning",
                chat_id=int(self.settings.TELEGRAM_CHAT_ID),
                warning_details=f"ID {target_id} autorizado.")
            
            self.logger.info(f"✅ ID autorizado: {target_id}")
            # Notificación al usuario autorizado
            try:
                await context.bot.send_message(
                    chat_id=target_id, 
                    text="🎉 Tu acceso ha sido aprobado. Ya puedes usar /start"
                )
            except Exception:
                self.logger.warning(f"No se pudo notificar al usuario {target_id} todavía.")
            
        except ValueError:
            await update.message.reply_text("❌ El ID debe ser un número entero.")

    @restricted
    async def check_ytdlp_version(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Verifica la versión del binario yt-dlp de forma segura.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        try:
            version = self.ytdlp_installer.get_version()
            if version:
                await self._send_ui_msg("ytdlp_version", update=update, version=version)
            else:
                await self._send_ui_msg("ytdlp_fail", update=update)
        except BotError as e:
            await update.message.reply_text(f"❌ Error de Sistema: {e.message}")
        except Exception as e:
            self.logger.error(f"Error inesperado: {e}")
            await update.message.reply_text("❌ Error interno al verificar versión.")

    @restricted    
    async def check_ytdlp_bins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Verifica si yt-dlp está instalado en el servidor.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        if self.ytdlp_installer.is_installed():
            await self._send_ui_msg("ytdlp_ok", update=update)
        else:
            await self._send_ui_msg("ytdlp_fail", update=update)

    @restricted
    async def install_ytdlp(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Ejecuta la instalación y reporta el progreso.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        await self._send_ui_msg("installing", update=update)
        try:
            self.ytdlp_installer.install()
            await self._send_ui_msg("ytdlp_ok", update=update)
        except Exception as e:
            # Notificamos al admin del error técnico y al usuario del fallo
            error_details = f"Fallo en instalación: {str(e)}"
            await self._send_ui_msg(
                "admin_notification_error", 
                update=update,
                chat_id=int(self.settings.TELEGRAM_CHAT_ID),
                error_details=error_details
            )

    @restricted
    async def update_ytdlp(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Manejador del comando /update. Comprueba y descarga la versión más reciente de yt-dlp.

        Args:
            update: Objeto que contiene los datos del evento de actualización de Telegram.
            context: El contexto de ejecución actual del bot.
        """
        # 1. Notificar inmediatamente al administrador que el proceso ha iniciado
        initial_msg = DownloaderBotMessages.pick_message("updating")
        progress_message = await update.message.reply_text(
            initial_msg, 
            parse_mode="HTML"
        )

        try:
            # 2. Ejecutar de forma segura la llamada síncrona en un hilo separado del pool de asyncio
            # Esto previene que las peticiones web lentas de GitHub congelen el Polling del bot.
            was_updated: bool = await asyncio.to_thread(self.ytdlp_installer.update_yt_dlp)

            if was_updated:
                # El binario cambió con éxito. Obtenemos la nueva versión para presentarla.
                new_version: str | None = await asyncio.to_thread(self.ytdlp_installer.get_version)
                version_str = new_version if new_version else "Desconocida"
                
                success_template = DownloaderBotMessages.pick_message("ytdlp_updated")
                version_template = DownloaderBotMessages.pick_message("ytdlp_version", args={"version": version_str})
                
                final_response = f"{success_template}\n\n{version_template}"
            else:
                # El binario ya estaba al día (update_yt_dlp devolvió False)
                current_version: str | None = await asyncio.to_thread(self.ytdlp_installer.get_version)
                version_str = current_version if current_version else "Desconocida"
                
                final_response = (
                    "✅ <b>yt-dlp</b> ya se encuentra actualizado en su última versión estable.\n\n"
                    f"{DownloaderBotMessages.pick_message('ytdlp_version', args={'version': version_str})}"
                )

            # 3. Editar el mensaje inicial con el resultado exitoso
            await progress_message.edit_text(final_response, parse_mode="HTML")

        except BinNotFoundError as e:
            self.logger.warning(f"Intento de actualización fallido: Binario ausente. {e.message}")
            fail_msg = DownloaderBotMessages.pick_message("ytdlp_fail")
            await progress_message.edit_text(
                f"{fail_msg}\n\n<i>Sugerencia: Ejecuta primero /install para inicializar el binario.</i>", 
                parse_mode="HTML"
            )

        except YTDLPError as e:
            self.logger.error(f"Fallo semántico controlado al actualizar yt-dlp: {e.message} - Detalles: {e.details}")
            error_base = DownloaderBotMessages.pick_message("ytdlp_update_fail")
            
            # Notificación técnica detallada para el administrador del sistema
            admin_alert = DownloaderBotMessages.pick_message(
                "admin_notification_error", 
                args={"error_details": f"Clase: {e.__class__.__name__}\nMotivo: {e.message}"}
            )
            await progress_message.edit_text(
                f"{error_base}\n\n{admin_alert}", 
                parse_mode="HTML"
            )

        except Exception as e:
            self.logger.critical(f"Excepción inesperada no controlada en el comando /update: {str(e)}", exc_info=True)
            error_base = DownloaderBotMessages.pick_message("ytdlp_update_fail")
            await progress_message.edit_text(
                f"{error_base}\n\n⚠️ <i>Ocurrió un error inesperado en el servidor. Revisa los logs para más detalles.</i>", 
                parse_mode="HTML"
            )
    
    @restricted
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Detecta una URL y pregunta el formato de descarga.

        Args:
            update: Objeto Update.
            context: Contexto de la aplicación.
        """
        url = update.message.text
        # Guardamos la URL en el contexto del usuario temporalmente
        context.user_data["current_url"] = url

        keyboard = [
            [
                InlineKeyboardButton("🎬 Video", callback_data=DownloadType.DL_VIDEO),
                InlineKeyboardButton("🎵 Solo Audio", callback_data=DownloadType.DL_AUDIO),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "He recibido el enlace. ¿Qué prefieres descargar?",
            reply_markup=reply_markup
        )

    def run(self) -> None:
            """
            Inicia el ciclo de ejecución de la aplicación.
            """
            self.logger.info("🚀 BotDownloader iniciado...")
            #self.stop_event = asyncio.Event()
            self.app.run_polling(stop_signals=None)

    def stop(self) -> None:
        """
        Detiene el bot de forma segura desde un hilo externo.
        """
        if self.app.running:
            self.logger.warning("Solicitando detención del bot...")
            if self._loop:
                self.logger.warning(f"Deteniendo el loop...")
                self._loop.call_soon_threadsafe(self.app.stop_running)
