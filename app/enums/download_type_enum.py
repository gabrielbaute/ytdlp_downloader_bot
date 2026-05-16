from enum import StrEnum

class DownloadType(StrEnum):
    """
    Tipo de archivo a descargar

    Attributes:
        DL_VIDEO (str): Descargar vídeo
        DL_AUDIO (str): Descargar audio
    """
    DL_VIDEO = "dl_video"
    DL_AUDIO = "dl_audio"