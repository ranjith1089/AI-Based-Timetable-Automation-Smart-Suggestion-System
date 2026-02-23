from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, EmailStr, Field, model_validator


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


class ConstraintRule(BaseModel):
    rule_id: str
    tenant_id: str
    name: str
    category: Literal["HARD", "SOFT"]
    weight: int = Field(ge=1, le=100)
    enabled: bool = True
    params: dict = Field(default_factory=dict)


class SubjectSpec(BaseModel):
    name: str
    course_code: str
    course_type: str
    l_hours: int = Field(ge=0)
    t_hours: int = Field(ge=0)
    p_hours: int = Field(ge=0)
    tcp: int = Field(ge=0)
    semester_id: str
    program_id: str
    regulation: str


class TimetableEntry(BaseModel):
    section: str
    day: str
    period: int
    subject: SubjectSpec | None = None
    course: str | None = None
    room: str
    faculty_id: str


class ElectiveGroup(BaseModel):
    group_name: str
    sections: list[str]
    electives: list[str]


class TimetableGenerateRequest(BaseModel):
    tenant_id: str
    sections: list[Union[str, "SchedulerSectionInput"]]
    courses: list[str] = Field(default_factory=list)
    subjects: list[SubjectSpec] = Field(default_factory=list)
    rooms: list[str]
    faculty_ids: list[str]
    working_days: int = Field(default=5, ge=1, le=6)
    hours_per_day: int = Field(default=6, ge=1, le=10)
    extra_hours: int = Field(default=0, ge=0, le=12)
    saturday_enabled: bool = False
    saturday_hours: int = Field(default=0, ge=0, le=10)
    lab_continuous_hours: int = Field(default=2, ge=1, le=4)

    @model_validator(mode="after")
    def normalize_course_inputs(self) -> "TimetableGenerateRequest":
        if not self.courses and self.subjects:
            self.courses = [subject.name for subject in self.subjects]

        if not self.courses:
            raise ValueError("At least one course or subject is required")

        if self.saturday_enabled:
            if self.working_days > 5:
                raise ValueError("working_days cannot exceed 5 when saturday_enabled is true")
            if self.saturday_hours <= 0:
                raise ValueError("saturday_hours must be greater than 0 when saturday_enabled is true")
        else:
            if self.saturday_hours != 0:
                raise ValueError("saturday_hours must be 0 when saturday_enabled is false")
            if self.working_days > 5:
                raise ValueError("working_days cannot exceed 5 when saturday_enabled is false")

        max_continuous_hours = max(self.hours_per_day, self.saturday_hours)
        if self.lab_continuous_hours > max_continuous_hours:
            raise ValueError("lab_continuous_hours cannot exceed configured daily maximum hours")

        return self


class TimetableGenerationConfig(BaseModel):
    working_days: int
    hours_per_day: int
    extra_hours: int
    saturday_enabled: bool
    saturday_hours: int
    lab_continuous_hours: int


class TimetableVersionRecord(BaseModel):
    timetable_id: str
    version: int
    tenant_id: str
    generation_config: TimetableGenerationConfig = Field(
        default_factory=lambda: TimetableGenerationConfig(
            working_days=5,
            hours_per_day=6,
            extra_hours=0,
            saturday_enabled=False,
            saturday_hours=0,
            lab_continuous_hours=2,
        )
    )


class ConflictRecord(BaseModel):
    conflict_type: Literal["FACULTY", "ROOM", "SECTION"]
    message: str
    section: str
    day: str
    period: int


class TimetableGenerateResponse(BaseModel):
    timetable_id: str = "generated"
    version: int = 1
    tenant_id: str
    generated: bool
    conflict_count: int
    quality_score: float
    generation_config: TimetableGenerationConfig = Field(
        default_factory=lambda: TimetableGenerationConfig(
            working_days=5,
            hours_per_day=6,
            extra_hours=0,
            saturday_enabled=False,
            saturday_hours=0,
            lab_continuous_hours=2,
        )
    )
    timetable: list[TimetableEntry]
    section_timetables: dict[str, list[TimetableEntry]] = Field(default_factory=dict)
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


class RoomSpec(BaseModel):
    room_id: str
    room_type: Literal["CLASSROOM", "LAB"] = "CLASSROOM"


class AdminConfig(BaseModel):
    working_days: int = 5
    hours_per_day: int = 6


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


class CurriculumImportResponse(BaseModel):
    imported: bool = True
    message: str = "Curriculum import completed"
