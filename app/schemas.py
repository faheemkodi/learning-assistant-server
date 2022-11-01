from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr


# User schemas
class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str
    invite_code: str


class UserGet(BaseModel):
    id: int
    superuser: bool
    active: Optional[bool]
    name: str
    kengram: Optional[str]
    level: Optional[int]
    goal_status: Optional[int]
    strength: Optional[int]
    progress: Optional[int]
    username: str
    email: EmailStr
    reset_code: Optional[str]
    expiry_date: Optional[datetime]
    creation_date: datetime

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    id: int
    name: str
    kengram: Optional[str]
    username: str
    email: EmailStr
    reset_code: Optional[str]

    class Config:
        orm_mode = True


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class PasswordResetCode(BaseModel):
    email: List[EmailStr]


class PasswordReset(BaseModel):
    email_address: EmailStr
    reset_code: str
    new_password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserManage(BaseModel):
    id: int

# Token schemas
class TokenData(BaseModel):
    id: Optional[str]


# Course schemas
class CourseCreate(BaseModel):
    name: str
    intensity: str
    goal: int
    goal_reset_date: Optional[datetime]
    deadline: datetime

    class Config:
        orm_mode = True


class CourseUpdate(BaseModel):
    id: int
    name: str
    kengram: Optional[str]
    stability: Optional[int]
    current_velocity: Optional[int]
    required_velocity: Optional[int]
    intensity: str
    goal: int
    goal_reset_date: Optional[datetime]
    deadline: datetime
    streak: int
    strength: int

    class Config:
        orm_mode = True


class CourseGet(BaseModel):
    id: int
    name: str
    kengram: Optional[str]
    progress: Optional[int]
    stability: Optional[int]
    current_velocity: Optional[int]
    required_velocity: Optional[int]
    intensity: str
    goal: int
    goal_status: Optional[int]
    goal_reset_date: Optional[datetime]
    deadline: datetime
    streak: int
    strength: int
    user_id: int
    creation_date: datetime

    class Config:
        orm_mode = True


# Lesson schemas
class LessonCreate(BaseModel):
    name: str
    course_id: int

    class Config:
        orm_mode = True


class LessonGet(BaseModel):
    id: int
    name: str
    kengram: Optional[str]
    progress: Optional[int]
    stability: Optional[int]
    course_id: int
    user_id: int
    creation_date: datetime

    class Config:
        orm_mode = True


class LessonUpdate(BaseModel):
    id: int
    name: str
    kengram: Optional[str]

    class Config:
        orm_mode = True


# Topic schemas
class TopicCreate(BaseModel):
    name: str
    lesson_id: int
    course_id: int

    class Config:
        orm_mode = True


class TopicGet(BaseModel):
    id: int
    name: str
    kengram: Optional[str]
    completed: bool
    revised: bool
    revision_count: int
    revision_date: Optional[datetime]
    stability: Optional[int]
    lesson_id: int
    course_id: int
    user_id: int
    creation_date: datetime

    class Config:
        orm_mode = True


class TopicUpdate(BaseModel):
    id: int
    name: str
    kengram: Optional[str]
    completed: bool
    revised: bool
    revision_count: int
    revision_date: Optional[datetime]
    stability: int

    class Config:
        orm_mode = True


# Burst schemas
class BurstCreate(BaseModel):
    course_id: int
    lesson_id: int
    duration: int
    interrupted: bool
    interruption: Optional[str]

    class Config:
        orm_mode = True


class BurstGet(BaseModel):
    id: int
    course_id: int
    lesson_id: int
    user_id: int
    duration: int
    interrupted: bool
    interruption: Optional[str]
    creation_date: datetime

    class Config:
        orm_mode = True


# Invite schemas
class InviteCreate(BaseModel):
    phone: str
    email: str
