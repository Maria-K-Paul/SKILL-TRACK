from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..models import (
    ActivityLog, Attempt, Certificate, Domain, Enrollment, Level, Slot, SlotBooking, User,
)
from ..rules import (
    DOMAIN_SELECTION_SEMESTER, current_enrollment, ensure_common_enrollment, get_settings, level_is_open, semester_of,
)
from ..schemas import EnrollIn

router = APIRouter(tags=["student"])

student_only = require_roles("student")


def _seats_taken(db: Session, slot_id: int) -> int:
    return db.scalar(select(func.count(SlotBooking.id)).where(SlotBooking.slot_id == slot_id)) or 0


@router.get("/me/dashboard")
def dashboard(user: User = Depends(student_only), db: Session = Depends(get_db)):
    cfg = get_settings(db)
    ensure_common_enrollment(db, user)
    db.commit()
    domains = db.scalars(select(Domain).where(Domain.is_common.is_(False)).order_by(Domain.id)).all()
    certs = db.execute(
        select(Certificate, Level, Domain)
        .join(Level, Level.id == Certificate.level_id)
        .join(Domain, Domain.id == Level.domain_id)
        .where(Certificate.user_id == user.id)
        .order_by(Certificate.issued_at)
    ).all()

    result = {
        "user": {"name": user.name, "department": user.department, "semester": user.semester},
        "domains": [{"id": d.id, "name": d.name} for d in domains],
        "points_to_unlock": cfg["points_to_unlock"],
        "max_attempts": cfg["max_attempts"],
        "enrollment": None,
        "levels": [],
        "slots": [],
        "booked_slot_id": None,
        "skill_gap": None,
        "certificates": [
            {
                "code": c.code, "title": f"{d.name} · {lv.name}",
                "issued_at": c.issued_at, "first_attempt": c.first_attempt,
            }
            for c, lv, d in certs
        ],
    }

    enr = current_enrollment(db, user)
    if enr is None:
        return result

    domain = db.get(Domain, enr.domain_id)
    result["enrollment"] = {
        "domain_id": domain.id, "domain": domain.name, "status": enr.status, "is_common": domain.is_common,
        "points": enr.points, "current_level": enr.current_level,
    }
    if domain.is_common:
        result["max_attempts"] = None  # common assessments have no attempt cap

    attempts = db.scalars(
        select(Attempt).where(Attempt.user_id == user.id, Attempt.level_id.in_([lv.id for lv in domain.levels]))
        .order_by(Attempt.attempt_no)
    ).all()
    by_level: dict[int, list[Attempt]] = {}
    for a in attempts:
        by_level.setdefault(a.level_id, []).append(a)

    active_level = None
    for lv in domain.levels:
        atts = by_level.get(lv.id, [])
        passed = next((a for a in atts if a.passed), None)
        if passed:
            state = "cleared"
        elif lv.number == enr.current_level and enr.status == "removed":
            state = "removed"
        elif level_is_open(user, enr, lv) and enr.status == "active":
            state = "active"
            active_level = lv
        else:
            state = "locked"
        result["levels"].append({
            "id": lv.id, "number": lv.number, "name": lv.name, "status": state,
            "attempts_used": len(atts),
            "score": atts[-1].score if atts else None,
            "first_attempt": bool(passed and passed.attempt_no == 1),
        })

    with_gaps = [a for a in attempts if a.skill_gaps]
    if with_gaps:
        latest = max(with_gaps, key=lambda a: a.taken_at)
        level = next(lv for lv in domain.levels if lv.id == latest.level_id)
        result["skill_gap"] = {"level_name": level.name, "weak": latest.skill_gaps}

    if active_level:
        # Fetch student's booked slot in this domain (any level)
        booked = db.scalar(
            select(SlotBooking.slot_id).join(Slot, Slot.id == SlotBooking.slot_id)
            .where(SlotBooking.user_id == user.id, Slot.domain_id == domain.id)
        )
        result["booked_slot_id"] = booked
        # Fetch all upcoming slots for this domain (students can book any slot regardless of level)
        slots = db.scalars(
            select(Slot).where(Slot.domain_id == domain.id, Slot.starts_at > datetime.now(timezone.utc))
            .order_by(Slot.starts_at)
        ).all()
        result["slots"] = [
            {
                "id": s.id, "starts_at": s.starts_at, "venue": s.venue,
                "seats_left": max(0, s.capacity - _seats_taken(db, s.id)),
            }
            for s in slots
        ]
    return result


@router.post("/enrollments", status_code=status.HTTP_201_CREATED)
def enroll(body: EnrollIn, user: User = Depends(student_only), db: Session = Depends(get_db)):
    domain = db.get(Domain, body.domain_id)
    if domain is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Domain not found")
    if domain.is_common:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Common assessments are assigned automatically")
    if semester_of(user) < DOMAIN_SELECTION_SEMESTER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Domain selection opens in Semester 3")

    cfg = get_settings(db)
    existing = db.scalars(
        select(Enrollment).join(Domain, Domain.id == Enrollment.domain_id)
        .where(Enrollment.user_id == user.id, Domain.is_common.is_(False))
    ).all()
    if any(e.domain_id == domain.id for e in existing):
        raise HTTPException(status.HTTP_409_CONFLICT, "Already enrolled in this domain")
    if any(e.status == "active" for e in existing) and max(e.points for e in existing) < cfg["points_to_unlock"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Earn {cfg['points_to_unlock']} points to unlock another domain")

    db.add(Enrollment(user_id=user.id, domain_id=domain.id))
    db.add(ActivityLog(user_id=user.id, action=f"{user.name} enrolled in {domain.name}"))
    db.commit()
    return {"domain_id": domain.id}


@router.post("/slots/{slot_id}/book")
def book_slot(slot_id: int, user: User = Depends(student_only), db: Session = Depends(get_db)):
    slot = db.get(Slot, slot_id)
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")

    # Check if student is enrolled in this domain
    domain = db.get(Domain, slot.domain_id)
    enr = db.scalar(select(Enrollment).where(
        Enrollment.user_id == user.id, Enrollment.domain_id == slot.domain_id, Enrollment.status == "active",
    ))
    if enr is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"You are not enrolled in {domain.name}")

    starts_at = slot.starts_at if slot.starts_at.tzinfo else slot.starts_at.replace(tzinfo=timezone.utc)
    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This slot has already started")
    already = db.scalar(select(SlotBooking).where(SlotBooking.slot_id == slot.id, SlotBooking.user_id == user.id))
    if already:
        return {"slot_id": slot.id}
    if _seats_taken(db, slot.id) >= slot.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "This slot is full")

    # One booking per domain: booking a new slot replaces the old one
    old = db.scalars(
        select(SlotBooking).join(Slot, Slot.id == SlotBooking.slot_id)
        .where(SlotBooking.user_id == user.id, Slot.domain_id == slot.domain_id)
    ).all()
    for booking in old:
        db.delete(booking)
    db.add(SlotBooking(slot_id=slot.id, user_id=user.id))
    db.add(ActivityLog(user_id=user.id, action=f"{user.name} booked a slot for {domain.name}"))
    db.commit()
    return {"slot_id": slot.id}
