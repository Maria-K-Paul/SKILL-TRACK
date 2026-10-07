from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ROLES = ("student", "owner", "admin", "invigilator")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    reg_no: Mapped[str | None] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="student")
    department: Mapped[str | None] = mapped_column(String(20))
    semester: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # The Semester 1-2 common assessments live in a special domain that students never pick themselves
    is_common: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    levels: Mapped[list["Level"]] = relationship(back_populates="domain", order_by="Level.number")


class Level(Base):
    __tablename__ = "levels"
    __table_args__ = (UniqueConstraint("domain_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"))
    number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    question_count: Mapped[int] = mapped_column(Integer, default=20)
    pass_mark: Mapped[int] = mapped_column(Integer, default=50)
    duration_min: Mapped[int] = mapped_column(Integer, default=30)
    easy_pct: Mapped[int] = mapped_column(Integer, default=30)
    medium_pct: Mapped[int] = mapped_column(Integer, default=50)
    hard_pct: Mapped[int] = mapped_column(Integer, default=20)
    domain: Mapped[Domain] = relationship(back_populates="levels")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    text: Mapped[str] = mapped_column(String(1000))
    options: Mapped[list] = mapped_column(JSON)
    answer_index: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(10))  # easy | medium | hard
    topic: Mapped[str | None] = mapped_column(String(100))


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "domain_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | removed
    current_level: Mapped[int] = mapped_column(Integer, default=1)
    points: Mapped[int] = mapped_column(Integer, default=0)


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    venue: Mapped[str] = mapped_column(String(120))
    capacity: Mapped[int] = mapped_column(Integer)


class SlotBooking(Base):
    __tablename__ = "slot_bookings"
    __table_args__ = (UniqueConstraint("slot_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    attempt_no: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    skill_gaps: Mapped[list | None] = mapped_column(JSON)
    topic_scores: Mapped[list | None] = mapped_column(JSON)  # every topic's score, not just the weak ones
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    first_attempt: Mapped[bool] = mapped_column(Boolean, default=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExamKey(Base):
    __tablename__ = "exam_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"))
    # level_id is optional - used only for keys generated without a slot (by specific level)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id"))
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # When set, only students who booked this slot can use the key
    slot_id: Mapped[int | None] = mapped_column(ForeignKey("slots.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    key_id: Mapped[int] = mapped_column(ForeignKey("exam_keys.id"))
    question_ids: Mapped[list] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    violations: Mapped[int] = mapped_column(Integer, default=0)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[int] = mapped_column(Integer)


class AiCache(Base):
    """Stored AI answers so Gemini is only called when the student's data changes."""
    __tablename__ = "ai_cache"
    __table_args__ = (UniqueConstraint("user_id", "kind", "cache_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(30))
    cache_key: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
