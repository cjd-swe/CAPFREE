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
    notes: Optional[str] = None

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
    game_date: Optional[datetime] = None
    grade_source: Optional[str] = None
    graded_at: Optional[datetime] = None

class PickCreate(PickBase):
    capper_name: str # Use name to lookup or create capper

class PickUpdate(BaseModel):
    result: Optional[PickResult] = None
    profit: Optional[float] = None

class PickGradeUpdate(BaseModel):
    result: PickResult
    # Profit will be calculated based on result, odds, and units_risked

class CapperUpdate(BaseModel):
    name: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    notes: Optional[str] = None

class CapperAnalytics(BaseModel):
    id: int
    name: str
    total_picks: int
    wins: int
    losses: int
    pushes: int
    pending: int
    win_rate: float
    roi: float
    total_profit: float
    total_units_risked: float
    recent_picks: List['Pick']
    
    class Config:
        from_attributes = True

class Pick(PickBase):
    id: int
    capper_id: int
    date: datetime
    capper: Capper

    class Config:
        from_attributes = True

class AutoGradeResult(BaseModel):
    total_pending: int
    graded_by_api: int
    auto_win: int
    skipped_not_final: int
    errors: List[str]


class BulkGradeRequest(BaseModel):
    pick_ids: List[int]
    result: PickResult


class BulkGradeResult(BaseModel):
    graded: int
    skipped: int


class NotificationBase(BaseModel):
    pick_id: Optional[int] = None
    message: str
    read: bool = False


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: int
    created_at: datetime

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
