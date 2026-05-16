from app.errors.base_error import DownloaderBotError

class BinNotFoundError(DownloaderBotError):
    """
    Raised when the yt-dlp binary is not found or is not executable.
    """
    def __init__(self, message: str = "yt-dlp binary not found", details: dict = None):
        super().__init__(message, details)
