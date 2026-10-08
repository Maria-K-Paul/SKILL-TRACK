"""Session-token checks: 15-minute access tokens, 1-day refresh tokens, renewal, expiry and token types.

    DATABASE_URL=<test db> python checks/set_demo_passwords.py
    DATABASE_URL=<test db> python checks/test_session_tokens.py
"""
import time
import uuid
import warnings

from _guard import require_test_database

require_test_database()
warnings.filterwarnings("ignore")

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

import seed  # noqa: E402
from app import security  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

client = TestClient(app)
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  -> ' + str(detail)) if detail else ''}")


def minutes_left(token):
    return round((jwt.decode(token, options={"verify_signature": False})["exp"] - time.time()) / 60)


def me(token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


def refresh(token):
    return client.post("/auth/refresh", json={"refresh_token": token})


# 1. Login returns both tokens with the right lifetimes
r = client.post("/auth/login", json={"email": "admin@college.edu", "password": seed.PASSWORD})
body = r.json()
access, refresh_token = body.get("access_token"), body.get("refresh_token")
check("login returns access + refresh tokens", r.status_code == 200 and bool(access and refresh_token), r.status_code)
check("access token lasts 15 min", minutes_left(access) == security.ACCESS_TOKEN_MINUTES, f"{minutes_left(access)} min")
check("refresh token lasts 1 day", minutes_left(refresh_token) == security.REFRESH_TOKEN_MINUTES, f"{minutes_left(refresh_token)} min")
check("access token marked type=access", jwt.decode(access, options={"verify_signature": False}).get("type") == "access")

# 2. Which token works where
auth = {"Authorization": f"Bearer {access}"}
check("access token works on /auth/me", me(access).status_code == 200)
check("access token works on an admin endpoint", client.get("/admin/overview", headers=auth).status_code == 200)
check("refresh token refused on /auth/me", me(refresh_token).status_code == 401)
check("access token refused on /auth/refresh", refresh(access).status_code == 401)

# 3. Refresh gives a new working access token, and no new refresh token
r = refresh(refresh_token)
check("refresh returns a new access token", r.status_code == 200 and "access_token" in r.json(), r.status_code)
check("new access token works", me(r.json().get("access_token", "")).status_code == 200)
check("refresh response has no new refresh token", "refresh_token" not in r.json())

# 4. Expiry
saved = security.ACCESS_TOKEN_MINUTES, security.REFRESH_TOKEN_MINUTES
security.ACCESS_TOKEN_MINUTES = -1
check("expired access token refused", me(security.create_access_token(1, "admin")).status_code == 401)
security.ACCESS_TOKEN_MINUTES = saved[0]
check("...but refresh still works after access expires", refresh(refresh_token).status_code == 200)
security.REFRESH_TOKEN_MINUTES = -1
r = refresh(security.create_refresh_token(1))
check("expired refresh token refused", r.status_code == 401, r.json().get("detail", ""))

# 5. A renewed access token never outlives the refresh token (sign in again 1 day after login)
security.REFRESH_TOKEN_MINUTES = 5
capped = refresh(security.create_refresh_token(1)).json()["access_token"]
security.REFRESH_TOKEN_MINUTES = saved[1]
check("access token capped at refresh expiry", minutes_left(capped) == 5, f"{minutes_left(capped)} min")

# 6. Tokens without a type (issued before session tokens) are refused
old_style = jwt.encode({"sub": "1", "role": "admin", "exp": int(time.time()) + 600}, security.SECRET_KEY, algorithm="HS256")
check("old-style token without type refused", me(old_style).status_code == 401)

# 7. Registration returns both tokens; a deactivated user cannot refresh
tag = uuid.uuid4().hex[:8]
email = f"token.test.{tag}@example.com"
r = client.post("/auth/register", json={"name": "Token Test", "email": email, "reg_no": f"TT{tag}",
                                        "password": "a-test-password", "department": "CSE"})
check("register returns both tokens", r.status_code == 201 and "refresh_token" in r.json(), r.status_code)
with SessionLocal() as db:
    db.scalar(select(User).where(User.email == email)).is_active = False
    db.commit()
check("deactivated user cannot refresh", refresh(r.json().get("refresh_token", "")).status_code == 401)

# 8. Wrong password
check("wrong password still 401", client.post("/auth/login", json={"email": "admin@college.edu", "password": "nope-nope"}).status_code == 401)

print(f"\n{sum(results)}/{len(results)} checks passed")
