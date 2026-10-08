"""Read-only: confirm a Neon test branch is separate from production and holds the same data.

    TEST_BRANCH_URL=<branch connection string> python checks/check_branch.py

Neon gives every branch its own timeline id; different ids prove that writes to the branch cannot reach production.
"""
import os

from _guard import host_of, production_url

from sqlalchemy import create_engine, inspect, text  # noqa: E402

PROD_URL = production_url() or exit("No DATABASE_URL found in skilltrack-api/.env.")
branch_url = os.environ.get("TEST_BRANCH_URL") or exit("Set TEST_BRANCH_URL to the Neon test branch connection string.")
if host_of(branch_url) == host_of(PROD_URL):
    exit("TEST_BRANCH_URL is the production database, not a branch.")


def info(url):
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1).replace("-pooler.", ".", 1))
    with engine.connect() as c:
        timeline = c.execute(text("SELECT current_setting('neon.timeline_id', true)")).scalar()
        counts = {t: c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in sorted(inspect(c).get_table_names())}
    return engine.url.host, timeline, counts


p_host, p_timeline, p_counts = info(PROD_URL)
b_host, b_timeline, b_counts = info(branch_url)
print("production :", p_host, "| timeline", p_timeline)
print("test branch:", b_host, "| timeline", b_timeline)
print("separate branches:", bool(p_timeline and b_timeline and p_timeline != b_timeline))
print(f"rows: production {sum(p_counts.values())}, test branch {sum(b_counts.values())}"
      f" -> {'same data' if p_counts == b_counts else 'different (normal once tests have written to the branch)'}")
