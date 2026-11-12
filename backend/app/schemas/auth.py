from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

Role = Literal["student", "faculty", "admin"]
Portal = Literal["student", "staff"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    portal: Portal


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: Role
    student_id: str | None = None
    program: str | None = None
    year: str | None = None
    title: str | None = None
    department: str | None = None


class DemoLogin(BaseModel):
    portal: Portal
    name: str
    note: str
    email: str
    password: str


class Message(BaseModel):
    detail: str
