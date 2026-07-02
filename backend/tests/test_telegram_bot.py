"""Tests for Telegram bot helpers, incl. PTB v21+ forward-origin handling."""
import datetime

from telegram import Chat, Message, MessageOriginHiddenUser, MessageOriginUser, User

from app.services.telegram_bot import _describe_message, _extract_forward_name

_CHAT = Chat(id=1, type="group", title="Picks Group")
_NOW = datetime.datetime.now(datetime.timezone.utc)


def _msg(**kwargs) -> Message:
    return Message(message_id=1, date=_NOW, chat=_CHAT, **kwargs)


def test_forward_name_none_for_regular_message():
    # Regression: accessing removed `forward_from` on PTB v21+ raised
    # AttributeError and crashed the photo handler on *every* message.
    assert _extract_forward_name(_msg()) is None


def test_forward_name_from_origin_user():
    origin = MessageOriginUser(
        date=_NOW, sender_user=User(id=7, is_bot=False, first_name="Sharp", last_name="Capper")
    )
    assert _extract_forward_name(_msg(forward_origin=origin)) == "Sharp Capper"


def test_forward_name_from_hidden_user():
    origin = MessageOriginHiddenUser(date=_NOW, sender_user_name="Hidden Capper")
    assert _extract_forward_name(_msg(forward_origin=origin)) == "Hidden Capper"


def test_describe_message_types():
    assert _describe_message(_msg(text="Lakers -3 2u")) == ("text", "Lakers -3 2u")
    assert _describe_message(_msg(text="/start")) == ("command", "/start")
    assert _describe_message(_msg()) == ("other", None)
