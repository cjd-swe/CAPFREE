from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class PickResult(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"
    PENDING = "PENDING"

class CapperBase(BaseModel):
    name: str
    telegram_chat_id: Optional[str] = None

class CapperCreate(CapperBase):
    pass

class Capper(CapperBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PickBase(BaseModel):
    sport: str
    league: Optional[str] = None
    match_key: Optional[str] = None
    pick_text: str
    units_risked: float
    odds: Optional[int] = None
    result: PickResult = PickResult.PENDING
    profit: float = 0.0
    original_image_path: Optional[str] = None
    raw_text: Optional[str] = None

class PickCreate(PickBase):
    capper_name: str # Use name to lookup or create capper

class PickUpdate(BaseModel):
    result: Optional[PickResult] = None
    profit: Optional[float] = None

class Pick(PickBase):
    id: int
    capper_id: int
    date: datetime
    capper: Capper

    class Config:
        from_attributes = True

class TelegramQueueBase(BaseModel):
    message_id: str
    chat_id: str
    photo_path: str

class TelegramQueue(TelegramQueueBase):
    id: int
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True
