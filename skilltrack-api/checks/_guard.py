"""Shared safety check for the scripts in this folder.

They write test data (passwords, bookings, keys), so they only run against a TEST database: a local copy or a
Neon test branch, given in DATABASE_URL. They refuse to run when DATABASE_URL points at the production host,
which they read from skilltrack-api/.env.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))  # so `app`, `seed` and Nizzy's test modules import from anywhere


def host_of(url: str) -> str:
    host = urlparse(url.replace("postgresql+psycopg://", "postgresql://")).hostname or ""
    return host.replace("-pooler.", ".")


def production_url() -> str | None:
    """DATABASE_URL as written in skilltrack-api/.env, ignoring any DATABASE_URL set in the shell
    (which normally points at the test database while these scripts run)."""
    env = API_DIR / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return None


def production_host() -> str | None:
    url = production_url()
    return host_of(url) if url else None


def require_test_database() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("Set DATABASE_URL to a TEST database (a local copy or a Neon test branch) first.")
    prod = production_host()
    if prod and host_of(url) == prod:
        sys.exit(f"Refusing to run: DATABASE_URL points at the production database ({prod}).")
    return url
