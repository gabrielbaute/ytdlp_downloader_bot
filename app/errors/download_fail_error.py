from app.errors.base_error import DownloaderBotError

class DownloadFail(DownloaderBotError):
    """
    Raised when a download process fails to complete or the file is not found.
    """
    def __init__(self, message: str = "Download failed", details: dict = None):
        super().__init__(message, details)
