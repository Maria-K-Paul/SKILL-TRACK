"""Print the number of rows in every table of a TEST database. Run before and after migrate_db.py to prove
that no data was lost.

    DATABASE_URL=<test db> python checks/row_counts.py BEFORE
"""
import os
import sys

from _guard import require_test_database

url = require_test_database()

from sqlalchemy import create_engine, inspect, text  # noqa: E402

engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1))
with engine.connect() as c:
    counts = {t: c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in sorted(inspect(c).get_table_names())}
print(sys.argv[1] if len(sys.argv) > 1 else "rows", counts, f"total={sum(counts.values())}")
