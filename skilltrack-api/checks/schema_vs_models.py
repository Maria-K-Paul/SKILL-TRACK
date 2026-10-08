"""Compare the app's models with the tables in a TEST database (run after migrate_db.py).

    DATABASE_URL=<test db> python checks/schema_vs_models.py

"MISSING" or "REQUIRED IN DB" lines are real problems: queries or inserts for those columns fail.
"""
from _guard import require_test_database

require_test_database()

from sqlalchemy import inspect  # noqa: E402

from app import models  # noqa: E402,F401  (registers tables)
from app.database import Base, engine  # noqa: E402

insp = inspect(engine)
db_tables = set(insp.get_table_names())
problems = 0
for table in Base.metadata.sorted_tables:
    if table.name not in db_tables:
        print(f"MISSING TABLE  {table.name}")
        problems += 1
        continue
    db_cols = {c["name"]: c for c in insp.get_columns(table.name)}
    for col in table.columns:
        if col.name not in db_cols:
            print(f"MISSING COLUMN {table.name}.{col.name}  (model: {col.type}, nullable={col.nullable})")
            problems += 1
        elif db_cols[col.name]["nullable"] and not col.nullable and not col.primary_key:
            print(f"nullable in DB but required in model (fine): {table.name}.{col.name}")
        elif not db_cols[col.name]["nullable"] and col.nullable:
            print(f"REQUIRED IN DB but optional in model: {table.name}.{col.name}  (inserts without it would fail)")
            problems += 1
    for name in set(db_cols) - {c.name for c in table.columns}:
        print(f"extra DB column, not in the model: {table.name}.{name} nullable={db_cols[name]['nullable']}")
print("serious mismatches:", problems)
