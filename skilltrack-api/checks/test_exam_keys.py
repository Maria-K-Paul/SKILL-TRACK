"""Exam-key checks: the Exam Keys page lists only active keys, and issuing a key deletes expired keys that no
exam used (10 minutes after they expire) while keeping keys an exam used.

    DATABASE_URL=<test db> python checks/test_exam_keys.py
"""
import uuid
import warnings
from datetime import datetime, timedelta, timezone

from _guard import require_test_database

require_test_database()
warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import security  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ExamKey, ExamSession, Level, Slot, User  # noqa: E402

client = TestClient(app)
results = []
now = datetime.now(timezone.utc)


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  -> ' + str(detail)) if detail else ''}")


def auth(user):
    return {"Authorization": f"Bearer {security.create_access_token(user.id, user.role)}"}


db = SessionLocal()
invigilator = db.scalar(select(User).where(User.role == "invigilator"))
admin = db.scalar(select(User).where(User.role == "admin"))
student = db.scalar(select(User).where(User.role == "student"))
slot = db.scalar(select(Slot).order_by(Slot.id.desc()))
level = db.get(Level, slot.level_id)

tag = uuid.uuid4().hex[:6].upper()
made = {}
for i, (name, minutes) in enumerate((("old_unused", -60), ("old_used", -60), ("just_expired", -2), ("active", 30))):
    key = ExamKey(code=f"TST{i}-{tag}", domain_id=slot.domain_id, slot_id=slot.id,
                  issued_by=invigilator.id, expires_at=now + timedelta(minutes=minutes))
    db.add(key)
    db.flush()
    made[name] = key.id
session = ExamSession(user_id=student.id, level_id=level.id, key_id=made["old_used"], question_ids=[],
                      ends_at=now - timedelta(minutes=30), submitted_at=now - timedelta(minutes=40))
db.add(session)
db.commit()

for who in (invigilator, admin):
    r = client.get("/exam/keys", headers=auth(who))
    ids = {k["id"] for k in r.json()} if r.status_code == 200 else set()
    check(f"{who.role}: list returns 200", r.status_code == 200, r.status_code)
    check(f"{who.role}: active key is listed", made["active"] in ids)
    check(f"{who.role}: no expired key is listed",
          not ids & {made["old_unused"], made["old_used"], made["just_expired"]}
          and all(k["seconds_left"] > 0 for k in r.json()))

r = client.post("/exam/keys", json={"slot_id": slot.id, "minutes": 5}, headers=auth(invigilator))
check("issuing a key returns 201", r.status_code == 201, r.status_code)
new_id = r.json().get("id") if r.status_code == 201 else None

db.expire_all()
check("unused key expired an hour ago is deleted", db.get(ExamKey, made["old_unused"]) is None)
check("key an exam used is kept", db.get(ExamKey, made["old_used"]) is not None)
check("key expired 2 minutes ago is kept for now (10-minute delay)", db.get(ExamKey, made["just_expired"]) is not None)
check("active key is kept", db.get(ExamKey, made["active"]) is not None)
left = db.scalars(select(ExamKey).where(ExamKey.expires_at <= now - timedelta(minutes=10))).all()
used = set(db.scalars(select(ExamSession.key_id)))
check("no unused key expired over 10 minutes ago is left", all(k.id in used for k in left),
      [k.code for k in left if k.id not in used])

r = client.get("/exam/keys", headers=auth(invigilator))
check("new key is listed", r.status_code == 200 and new_id in {k["id"] for k in r.json()})

# Clean up what this script added
db.delete(db.get(ExamSession, session.id))
db.flush()
for key_id in [*made.values(), new_id]:
    if key_id and (key := db.get(ExamKey, key_id)):
        db.delete(key)
db.commit()
db.close()

print(f"\n{sum(results)}/{len(results)} passed")
