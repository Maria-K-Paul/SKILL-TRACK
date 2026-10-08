"""Call the main API endpoints as each role against a TEST database and report any server errors (5xx).

    DATABASE_URL=<test db> python checks/smoke_roles.py

It gives the seeded admin, owner, invigilator and two demo students a throwaway password in that TEST
database, logs in as each, and calls their pages' endpoints, including issuing an exam key.
"""
import warnings

from _guard import require_test_database

require_test_database()
warnings.filterwarnings("ignore")

import bcrypt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Slot, User  # noqa: E402

TEST_PW = "copy-test-pass"
ACCOUNTS = ("admin@college.edu", "owner@college.edu", "invigilator@college.edu", "arun@college.edu", "divya@college.edu")

client = TestClient(app, raise_server_exceptions=False)
with SessionLocal() as db:
    for email in ACCOUNTS:
        db.scalar(select(User).where(User.email == email)).password_hash = bcrypt.hashpw(TEST_PW.encode(), bcrypt.gensalt(4)).decode()
    db.commit()
    slot_id = db.scalars(select(Slot.id).order_by(Slot.starts_at.desc())).first()


def login(email):
    r = client.post("/auth/login", json={"email": email, "password": TEST_PW})
    assert r.status_code == 200, (email, r.status_code, r.text[:200])
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


failures = 0


def call(role, method, path, headers, **kw):
    global failures
    r = client.request(method, path, headers=headers, **kw)
    bad = r.status_code >= 500
    failures += bad
    detail = r.text[:140].replace("\n", " ") if r.status_code >= 400 else ""
    print(f"{'ERROR' if bad else 'ok   '} {r.status_code} {role:<11} {method} {path} {detail}")


PLAN = {
    "admin@college.edu": ("admin", [("GET", "/admin/overview"), ("GET", "/admin/students"), ("GET", "/admin/activity"),
                                    ("GET", "/admin/users"), ("GET", "/admin/domains"), ("GET", "/admin/settings"),
                                    ("GET", "/manage/slots/catalog"), ("GET", "/exam/keys"), ("GET", "/exam/slots"),
                                    ("GET", "/exam/catalog")]),
    "owner@college.edu": ("owner", [("GET", "/owner/overview"), ("GET", "/manage/slots/catalog")]),
    "invigilator@college.edu": ("invigilator", [("GET", "/exam/keys"), ("GET", "/exam/slots"), ("GET", "/exam/catalog"),
                                                ("POST", "/exam/keys", {"json": {"slot_id": slot_id}}), ("GET", "/exam/keys")]),
    "arun@college.edu": ("student", [("GET", "/auth/me"), ("GET", "/me/dashboard"), ("GET", "/me/bookings"),
                                     ("GET", "/me/credentials"), ("GET", "/domains"), ("GET", "/exam/my-slot")]),
    "divya@college.edu": ("student", [("GET", "/me/dashboard"), ("GET", "/me/bookings"), ("GET", "/me/credentials")]),
}
for email, (role, calls) in PLAN.items():
    headers = login(email)
    for item in calls:
        call(role, item[0], item[1], headers, **(item[2] if len(item) > 2 else {}))
print(f"\nserver errors: {failures}")
