from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, EmailStr, Field, model_validator


class SubjectSpec(BaseModel):
    subject_id: str | None = None
    name: str
    course_code: str = Field(min_length=2)
    course_type: Literal["THEORY", "PRACTICAL", "TUTORIAL", "PROJECT"]
    l_hours: int = Field(ge=0)
    t_hours: int = Field(ge=0)
    p_hours: int = Field(ge=0)
    tcp: int = Field(ge=0)
    semester_id: str = Field(min_length=2)
    program_id: str = Field(min_length=2)
    regulation: str = Field(min_length=2)


class User(BaseModel):
    user_id: str = Field(min_length=2)
    tenant_id: str = Field(min_length=2)
    name: str
    email: EmailStr
    role: str


class AccessScope(BaseModel):
    user_id: str
    role_id: str
    tenant_id: str
    scope_type: Literal["TENANT", "INSTITUTE", "DEPARTMENT", "PROGRAM", "SECTION"]
    scope_id: str
    can_view: bool = True
    can_edit: bool = False
    can_approve: bool = False
    can_publish: bool = False


class FacultyAvailability(BaseModel):
    faculty_id: str
    available_slots: list[str]


class ConstraintRule(BaseModel):
    rule_id: str
    tenant_id: str
    name: str
    category: Literal["HARD", "SOFT"]
    weight: int = Field(ge=1, le=100)
    enabled: bool = True
    params: dict = Field(default_factory=dict)


class TimetableEntry(BaseModel):
    section: str
    day: str
    period: int
    subject: SubjectSpec
    room: str
    faculty_id: str


class ElectiveGroup(BaseModel):
    group_name: str
    sections: list[str]
    electives: list[str]


class SaturdayConfig(BaseModel):
    enabled: bool = False
    mode: Literal["LABS_ONLY", "SD_ELECTIVE_FOCUS", "OVERFLOW"] = "OVERFLOW"
    max_periods: int = Field(default=4, ge=1, le=8)


class ExtraHourBuffer(BaseModel):
    enabled: bool = False
    periods: int = Field(default=0, ge=0, le=3)


class TimetableGenerateRequest(BaseModel):
    tenant_id: str
    sections: list[Union[str, "SchedulerSectionInput"]]
    courses: list[str] = Field(default_factory=list)
    rooms: list[str]
    faculty_ids: list[str] = Field(default_factory=list)
    admin_config: Optional["SchedulerAdminConfig"] = None
    room_types: dict[str, Literal["CLASSROOM", "LAB"]] = Field(default_factory=dict)
    ga_config: dict[str, float | int] = Field(default_factory=dict)


class ConflictRecord(BaseModel):
    conflict_type: Literal["FACULTY", "ROOM", "SECTION"]
    message: str
    section: str
    day: str
    period: int


class TimetableGenerateResponse(BaseModel):
    tenant_id: str
    generated: bool
    conflict_count: int
    quality_score: float
    timetable: list[TimetableEntry]
    section_timetables: dict[str, list[TimetableEntry]]
    allocation_rationale: list[str] = Field(default_factory=list)


class SchedulerSubjectInput(BaseModel):
    code: str
    ltp: str
    faculty_id: str
    room_type: Literal["CLASSROOM", "LAB"] = "CLASSROOM"
    elective_group: str | None = None
    lab_block_size: int | None = None


class SchedulerSectionInput(BaseModel):
    section: str
    subjects: list[SchedulerSubjectInput]


class SchedulerAdminConfig(BaseModel):
    working_days: list[str]
    hours_per_day: int = Field(ge=1)
    extra_hours: dict[str, int] = Field(default_factory=dict)
    saturday_hours: int | None = Field(default=None, ge=1)
    allowed_lab_block_sizes: list[int] = Field(default_factory=lambda: [2, 3, 4])
    default_lab_block_size: int = 2


class SchedulerGenerateResult(TimetableGenerateResponse):
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    fitness_score: float
    constraint_summary: dict


class TimetableValidateRequest(BaseModel):
    tenant_id: str
    timetable: list[TimetableEntry]
    elective_groups: list[ElectiveGroup] = Field(default_factory=list)


class SuggestionRecord(BaseModel):
    suggestion_id: str
    suggestion_type: Literal["SWAP", "LOAD_BALANCE", "IDLE_ROOM"]
    description: str
    expected_quality_delta: float


class SuggestionResponse(BaseModel):
    tenant_id: str
    suggestions: list[SuggestionRecord]


class SimulationRequest(BaseModel):
    tenant_id: str
    scenario_name: str
    scenario_type: Literal["ADD_SECTION", "FACULTY_LEAVE", "HOLIDAY", "FIVE_DAY_WEEK"]
    payload: dict = Field(default_factory=dict)


class SimulationResponse(BaseModel):
    tenant_id: str
    scenario_name: str
    impact_summary: str
    estimated_conflicts: int
    estimated_quality_score: float


class EmergencyRescheduleRequest(BaseModel):
    tenant_id: str
    reason: str
    affected_faculty_id: str
    section: str


class EmergencyRescheduleResponse(BaseModel):
    tenant_id: str
    handled: bool
    substitute_faculty_id: str
    recommendation: str


class QualityResponse(BaseModel):
    tenant_id: str
    faculty_load_balance: float
    student_fatigue: float
    room_utilization: float
    clash_risk: float
    overall_quality: float


class ExtractedSubject(BaseModel):
    semester: str
    code: str
    name: str
    course_type: str
    L: int = Field(ge=0)
    T: int = Field(ge=0)
    P: int = Field(ge=0)
    TCP: int = Field(ge=0)
    credits: int = Field(ge=0)


class SubjectImportResponse(BaseModel):
    semesters: dict[str, list[ExtractedSubject]]
    errors: list[dict] = Field(default_factory=list)
    total_subjects: int
