from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from .config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30
COOKIE_NAME = "sharpwatch_token"


class LoginRequest(BaseModel):
    password: str


def _create_token() -> str:
    payload = {
        "sub": "user",
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def _verify_token(token: str) -> bool:
    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return True
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False


async def require_auth(request: Request):
    """FastAPI dependency — raises 401 if auth is enabled and token is missing/invalid."""
    if not settings.APP_PASSWORD:
        return  # auth disabled
    token = request.cookies.get(COOKIE_NAME)
    if not token or not _verify_token(token):
        raise HTTPException(status_code=401, detail="Not authenticated")


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    if not settings.APP_PASSWORD:
        return {"authenticated": True}
    if body.password != settings.APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong password")
    token = _create_token()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=TOKEN_EXPIRE_DAYS * 86400,
        samesite="lax",
    )
    return {"authenticated": True}


@router.get("/me")
async def me(request: Request):
    if not settings.APP_PASSWORD:
        return {"authenticated": True}
    token = request.cookies.get(COOKIE_NAME)
    if not token or not _verify_token(token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"authenticated": False}
