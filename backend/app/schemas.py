from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    user_id: str = Field(min_length=3)
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


class TimetableGenerateRequest(BaseModel):
    tenant_id: str
    sections: list[str]
    courses: list[str]
    rooms: list[str]


class TimetableGenerateResponse(BaseModel):
    tenant_id: str
    generated: bool
    conflict_count: int
    quality_score: float
    timetable: list[dict]
