"""Give admin@college.edu and arun@college.edu the public demo password from seed.py, in a TEST database only.
Nizzy's test_new_features.py logs in with that password.

    DATABASE_URL=<test db> python checks/set_demo_passwords.py
"""
from _guard import require_test_database

require_test_database()

import bcrypt  # noqa: E402
from sqlalchemy import select  # noqa: E402

import seed  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

with SessionLocal() as db:
    for email in ("admin@college.edu", "arun@college.edu"):
        db.scalar(select(User).where(User.email == email)).password_hash = bcrypt.hashpw(
            seed.PASSWORD.encode(), bcrypt.gensalt(4)).decode()
    db.commit()
print("demo passwords set (test database only)")
