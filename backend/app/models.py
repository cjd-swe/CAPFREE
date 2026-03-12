from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class PickResult(str, enum.Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"
    PENDING = "PENDING"

class Capper(Base):
    __tablename__ = "cappers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    telegram_chat_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    picks = relationship("Pick", back_populates="capper")

class Pick(Base):
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True, index=True)
    capper_id = Column(Integer, ForeignKey("cappers.id"))
    date = Column(DateTime, default=datetime.utcnow)
    sport = Column(String, index=True)
    league = Column(String)
    match_key = Column(String, index=True) # e.g. "LAL vs BOS"
    pick_text = Column(String)
    units_risked = Column(Float)
    odds = Column(Integer, nullable=True)
    result = Column(String, default=PickResult.PENDING.value) # Storing as string for simplicity with SQLite
    profit = Column(Float, default=0.0)
    original_image_path = Column(String, nullable=True)
    raw_text = Column(String, nullable=True)
    game_date = Column(DateTime, nullable=True)    # when the game is played (used for ESPN lookups)
    grade_source = Column(String, nullable=True)  # "manual" | "espn_api" | "auto_win"
    graded_at = Column(DateTime, nullable=True)

    capper = relationship("Capper", back_populates="picks")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    pick_id = Column(Integer, ForeignKey("picks.id", ondelete="CASCADE"), nullable=True)
    message = Column(String)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TelegramQueue(Base):
    __tablename__ = "telegram_queue"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String)
    chat_id = Column(String)
    photo_path = Column(String)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
