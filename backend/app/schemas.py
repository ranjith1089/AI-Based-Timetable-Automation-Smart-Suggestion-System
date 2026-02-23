from typing import Literal

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
    course: str
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
    sections: list[str]
    section_count: int | None = Field(default=None, ge=1)
    section_groups: dict[str, list[str]] = Field(default_factory=dict)
    courses: list[str]
    rooms: list[str]
    faculty_ids: list[str]
    elective_groups: list[ElectiveGroup] = Field(default_factory=list)
    saturday_config: SaturdayConfig = Field(default_factory=SaturdayConfig)
    extra_hour_buffer: ExtraHourBuffer = Field(default_factory=ExtraHourBuffer)
    enforce_lab_continuity: bool = True

    @model_validator(mode="after")
    def validate_section_count(self) -> "TimetableGenerateRequest":
        expected_count = self.section_count or len(self.sections)
        if expected_count != len(self.sections):
            raise ValueError("section_count must match number of sections supplied")
        return self


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


class TimetableValidateRequest(BaseModel):
    tenant_id: str
    timetable: list[TimetableEntry]


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
