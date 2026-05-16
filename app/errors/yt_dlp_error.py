from app.errors.base_error import DownloaderBotError

class YTDLPError(DownloaderBotError):
    """
    Raised when an error occurs during the execution of yt-dlp.
    """
    def __init__(self, message: str = "Error executing yt-dlp", details: dict = None):
        super().__init__(message, details)
