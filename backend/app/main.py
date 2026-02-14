import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    AccessScope,
    ConstraintRule,
    EmergencyRescheduleRequest,
    EmergencyRescheduleResponse,
    QualityResponse,
    SimulationRequest,
    SimulationResponse,
    SuggestionResponse,
    TimetableGenerateRequest,
    TimetableGenerateResponse,
    TimetableValidateRequest,
    User,
)
from .services import (
    build_suggestions,
    calculate_quality,
    detect_conflicts,
    emergency_reschedule,
    run_simulation,
    validate_constraints,
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
MOCK_SCOPES: list[AccessScope] = []
MOCK_CONSTRAINTS: list[ConstraintRule] = []
TIMETABLE_CACHE: dict[str, TimetableGenerateResponse] = {}


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
    MOCK_SCOPES.append(scope)
    return scope


@app.post("/constraints", response_model=ConstraintRule)
def create_constraint(rule: ConstraintRule) -> ConstraintRule:
    errors = validate_constraints(MOCK_CONSTRAINTS + [rule])
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    MOCK_CONSTRAINTS.append(rule)
    return rule


@app.get("/constraints", response_model=list[ConstraintRule])
def list_constraints(tenant_id: str) -> list[ConstraintRule]:
    return [rule for rule in MOCK_CONSTRAINTS if rule.tenant_id == tenant_id]


@app.post("/timetables/validate")
def validate_timetable(payload: TimetableValidateRequest) -> dict:
    conflicts = detect_conflicts(payload.timetable)
    return {
        "tenant_id": payload.tenant_id,
        "valid": len(conflicts) == 0,
        "conflict_count": len(conflicts),
        "conflicts": [conflict.model_dump() for conflict in conflicts],
    }


@app.post("/timetables/generate", response_model=TimetableGenerateResponse)
def generate_timetable(payload: TimetableGenerateRequest) -> TimetableGenerateResponse:
    if not payload.courses or not payload.rooms or not payload.faculty_ids:
        raise HTTPException(status_code=400, detail="courses, rooms, and faculty_ids are required")

    entries = []
    for i, section in enumerate(payload.sections, start=1):
        entries.append(
            {
                "section": section,
                "day": "Monday",
                "period": i,
                "course": payload.courses[(i - 1) % len(payload.courses)],
                "room": payload.rooms[(i - 1) % len(payload.rooms)],
                "faculty_id": payload.faculty_ids[(i - 1) % len(payload.faculty_ids)],
            }
        )

    response = TimetableGenerateResponse(
        tenant_id=payload.tenant_id,
        generated=True,
        conflict_count=0,
        quality_score=82.0,
        timetable=entries,
    )
    timetable_id = str(uuid4())
    TIMETABLE_CACHE[timetable_id] = response
    return response


@app.post("/timetables/suggestions", response_model=SuggestionResponse)
def timetable_suggestions(payload: TimetableValidateRequest) -> SuggestionResponse:
    conflicts = detect_conflicts(payload.timetable)
    return build_suggestions(payload.tenant_id, payload.timetable, len(conflicts))


@app.post("/simulations", response_model=SimulationResponse)
def simulate(payload: SimulationRequest) -> SimulationResponse:
    return run_simulation(payload)


@app.post("/reschedule/emergency", response_model=EmergencyRescheduleResponse)
def handle_emergency(payload: EmergencyRescheduleRequest) -> EmergencyRescheduleResponse:
    faculty_pool = [user.user_id for user in MOCK_USERS if user.tenant_id == payload.tenant_id] or [payload.affected_faculty_id]
    return emergency_reschedule(payload, faculty_pool)


@app.post("/timetables/quality", response_model=QualityResponse)
def timetable_quality(payload: TimetableValidateRequest) -> QualityResponse:
    conflicts = detect_conflicts(payload.timetable)
    return calculate_quality(payload.tenant_id, payload.timetable, len(conflicts))
