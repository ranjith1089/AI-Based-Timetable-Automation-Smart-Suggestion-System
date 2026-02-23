import os
from contextlib import asynccontextmanager
from uuid import uuid4

from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .database import check_connection, _get_engine
from .pdf_ingestion import extract_raw_tables, normalize_subject_rows
from .schemas import (
    AccessScope,
    ConstraintRule,
    ElectiveGroup,
    EmergencyRescheduleRequest,
    EmergencyRescheduleResponse,
    CurriculumImportResponse,
    QualityResponse,
    SimulationRequest,
    SimulationResponse,
    SubjectImportResponse,
    SuggestionResponse,
    SubjectSpec,
    TimetableGenerateRequest,
    TimetableGenerateResponse,
    TimetableValidateRequest,
    User,
    AdminConfig,
    RoomSpec,
)
from .scheduler_engine import SchedulerEngine
from .services import (
    build_suggestions,
    calculate_quality,
    detect_conflicts,
    generate_timetable_entries,
    emergency_reschedule,
    generate_timetable_entries,
    run_simulation,
    generate_section_aware_timetable,
    validate_constraints,
)

api_title = os.getenv("API_TITLE", "AI Timetable Automation API")
api_version = os.getenv("API_VERSION", "0.1.0")
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    status = check_connection()
    if status["method"] == "postgres":
        print("Connected to Supabase PostgreSQL directly")
    elif status["method"] == "rest_api":
        print("Connected to Supabase via REST API (HTTPS)")
    else:
        print("WARNING: No database connection — running with in-memory storage only")
    yield
    try:
        _get_engine().dispose()
    except Exception:
        pass


app = FastAPI(title=api_title, version=api_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_USERS: list[User] = []
MOCK_SCOPES: list[AccessScope] = []
MOCK_CONSTRAINTS: list[ConstraintRule] = []
MOCK_ELECTIVE_GROUPS: list[ElectiveGroup] = []
TIMETABLE_CACHE: dict[str, TimetableGenerateResponse] = {}
SCHEDULER_ENGINE = SchedulerEngine(seed=42)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-health")
def db_health() -> dict:
    status = check_connection()
    if status["method"]:
        return {"status": "ok", "database": "connected", "method": status["method"]}
    raise HTTPException(status_code=503, detail="Database connection failed")


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



@app.post("/elective-groups", response_model=ElectiveGroup)
def create_elective_group(group: ElectiveGroup) -> ElectiveGroup:
    MOCK_ELECTIVE_GROUPS.append(group)
    return group


@app.get("/elective-groups", response_model=list[ElectiveGroup])
def list_elective_groups(section: str | None = None) -> list[ElectiveGroup]:
    if not section:
        return MOCK_ELECTIVE_GROUPS
    return [group for group in MOCK_ELECTIVE_GROUPS if section in group.sections]


@app.post("/timetables/validate")
def validate_timetable(payload: TimetableValidateRequest) -> dict:
    conflicts = detect_conflicts(payload.timetable, payload.elective_groups)
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

    entries, rationale = generate_timetable_entries(payload)
    conflicts = detect_conflicts(entries)
    quality = calculate_quality(payload.tenant_id, entries, len(conflicts))

    section_timetables = {section: [entry for entry in entries if entry.section == section] for section in payload.sections}
    response = TimetableGenerateResponse(
        tenant_id=payload.tenant_id,
        generated=True,
        conflict_count=len(conflicts),
        quality_score=quality.overall_quality,
        timetable=entries,
        section_timetables=section_timetables,
        allocation_rationale=rationale,
    )
    timetable_id = str(uuid4())
    TIMETABLE_CACHE[timetable_id] = response
    return response


@app.post("/timetables/suggestions", response_model=SuggestionResponse)
def timetable_suggestions(payload: TimetableValidateRequest) -> SuggestionResponse:
    conflicts = detect_conflicts(payload.timetable, payload.elective_groups)
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
    conflicts = detect_conflicts(payload.timetable, payload.elective_groups)
    return calculate_quality(payload.tenant_id, payload.timetable, len(conflicts))


@app.post("/subjects/import-pdf", response_model=SubjectImportResponse)
async def import_subjects_pdf(
    pdf_content: bytes = Body(..., media_type="application/pdf"),
) -> SubjectImportResponse:
    if not pdf_content:
        raise HTTPException(status_code=400, detail="Empty PDF payload")

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_content)
        tmp_path = tmp.name

    try:
        rows = extract_raw_tables(tmp_path)
        semesters, errors = normalize_subject_rows(rows)
        total_subjects = sum(len(subjects) for subjects in semesters.values())
        return SubjectImportResponse(semesters=semesters, errors=errors, total_subjects=total_subjects)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

