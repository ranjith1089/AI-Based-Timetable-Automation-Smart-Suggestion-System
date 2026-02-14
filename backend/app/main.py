import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    AccessScope,
    TimetableGenerateRequest,
    TimetableGenerateResponse,
    User,
)

api_title = os.getenv("API_TITLE", "AI Timetable Automation API")
api_version = os.getenv("API_VERSION", "0.1.0")
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app = FastAPI(title=api_title, version=api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_USERS: list[User] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users", response_model=User)
def create_user(user: User) -> User:
    if any(existing.email == user.email for existing in MOCK_USERS):
        raise HTTPException(status_code=409, detail="Email already exists")
    MOCK_USERS.append(user)
    return user


@app.get("/users", response_model=list[User])
def list_users() -> list[User]:
    return MOCK_USERS


@app.post("/access/scope", response_model=AccessScope)
def assign_scope(scope: AccessScope) -> AccessScope:
    return scope


@app.post("/timetables/generate", response_model=TimetableGenerateResponse)
def generate_timetable(payload: TimetableGenerateRequest) -> TimetableGenerateResponse:
    slots = []
    for i, section in enumerate(payload.sections, start=1):
        slots.append(
            {
                "section": section,
                "day": "Monday",
                "period": i,
                "course": payload.courses[(i - 1) % len(payload.courses)],
                "room": payload.rooms[(i - 1) % len(payload.rooms)],
            }
        )

    return TimetableGenerateResponse(
        tenant_id=payload.tenant_id,
        generated=True,
        conflict_count=0,
        quality_score=82.0,
        timetable=slots,
    )
