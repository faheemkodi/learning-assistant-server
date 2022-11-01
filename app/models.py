from enum import unique
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    superuser = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    kengram = Column(String)
    level = Column(Integer, default=0)
    goal_status = Column(Integer, default=0)
    progress = Column(Integer, default=0)
    strength = Column(Integer, default=0)
    invite_code = Column(String, nullable=False)
    reset_code = Column(String)
    expiry_date = Column(TIMESTAMP(timezone=True))

    creation_date = Column(TIMESTAMP(timezone=True),
                           server_default=text("now()"))


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    kengram = Column(String)
    progress = Column(Integer, default=0)
    stability = Column(Integer, default=0)
    current_velocity = Column(Integer, default=0)
    required_velocity = Column(Integer, default=0)
    intensity = Column(String, nullable=False)
    goal = Column(Integer, nullable=False)
    goal_status = Column(Integer, default=0)
    deadline = Column(TIMESTAMP(timezone=True), nullable=False)
    streak = Column(Integer, default=0)
    strength = Column(Integer, default=0)
    goal_reset_date = Column(TIMESTAMP(timezone=True))

    creation_date = Column(TIMESTAMP(timezone=True),
                           server_default=text("now()"))

    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    kengram = Column(String)
    progress = Column(Integer, default=0)
    stability = Column(Integer, default=0)

    creation_date = Column(TIMESTAMP(timezone=True),
                           server_default=text("now()"))

    course_id = Column(Integer, ForeignKey(
        "courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    course = relationship("Course")
    user = relationship("User")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    kengram = Column(String)
    completed = Column(Boolean, default=False)
    revised = Column(Boolean, default=False)
    revision_count = Column(Integer, default=0)
    revision_date = Column(TIMESTAMP(timezone=True))
    stability = Column(Integer, default=0)

    creation_date = Column(TIMESTAMP(timezone=True),
                           server_default=text("now()"))

    course_id = Column(Integer, ForeignKey(
        "courses.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey(
        "lessons.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    course = relationship("Course")
    lesson = relationship("Lesson")
    user = relationship("User")


class Burst(Base):
    __tablename__ = "bursts"

    id = Column(Integer, primary_key=True, nullable=False)
    duration = Column(Integer, default=0)
    interrupted = Column(Boolean, default=False)
    interruption = Column(String)

    creation_date = Column(TIMESTAMP(timezone=True),
                           server_default=text("now()"))

    course_id = Column(Integer, ForeignKey(
        "courses.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey(
        "lessons.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    course = relationship("Course")
    lesson = relationship("Lesson")
    user = relationship("User")


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, nullable=False)
    invite_code = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"))
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    invoice = Column(String)
    event_id = Column(String, nullable=False)

    user = relationship("User")

    creation_date = Column(TIMESTAMP(timezone=True),
                           server_default=text("now()"))
