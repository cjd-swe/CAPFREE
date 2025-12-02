from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import picks, upload, telegram, analytics, settings

app = FastAPI(title="SharpWatch API")

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(picks.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to SharpWatch API"}
