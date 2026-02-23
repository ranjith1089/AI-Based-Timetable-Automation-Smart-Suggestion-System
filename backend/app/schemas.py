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


class TimetableGenerateRequest(BaseModel):
    tenant_id: str
    sections: list[str]
    courses: list[str]
    rooms: list[str]
    faculty_ids: list[str]
    working_days: int = Field(default=5, ge=1, le=6)
    hours_per_day: int = Field(default=6, ge=1, le=10)
    extra_hours: int = Field(default=0, ge=0, le=12)
    saturday_enabled: bool = False
    saturday_hours: int = Field(default=0, ge=0, le=10)
    lab_continuous_hours: int = Field(default=2, ge=1, le=4)

    @model_validator(mode="after")
    def validate_generation_config(self) -> "TimetableGenerateRequest":
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
    generation_config: TimetableGenerationConfig


class ConflictRecord(BaseModel):
    conflict_type: Literal["FACULTY", "ROOM", "SECTION"]
    message: str
    section: str
    day: str
    period: int


class TimetableGenerateResponse(BaseModel):
    timetable_id: str
    version: int
    tenant_id: str
    generated: bool
    conflict_count: int
    quality_score: float
    generation_config: TimetableGenerationConfig
    timetable: list[TimetableEntry]


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
