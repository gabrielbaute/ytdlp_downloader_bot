from app.errors.base_error import DownloaderBotError

class BotError(DownloaderBotError):
    """
    Raised when an error occurs within the bot's core logic or interaction.
    """
    def __init__(self, message: str = "An error occurred in the bot", details: dict = None):
        super().__init__(message, details)