from pydantic import BaseModel
from typing import Optional, List

class ChatID(BaseModel):
    """
    Detalles de un chat de Telegram.

    Attributes:
        chat_id (int): ID del chat de Telegram.
        username (Optional[str]): Nombre de usuario del chat.
        first_name (Optional[str]): Nombre del chat.
        last_name (Optional[str]): Apellido del chat.
    """
    chat_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class ChatIDList(BaseModel):
    """
    Lista de detalles de chats de Telegram.

    Attributes:
        count (int): Número total de chats.
        chats (List[ChatID]): Lista de detalles de chats.
    """
    count: int
    authorized_chats: List[ChatID] = []