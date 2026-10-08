"""Copy the production database (read-only) into an empty TEST database, and optionally save a JSON backup.

    python checks/copy_database.py --target postgresql://postgres:@127.0.0.1:5432/prodcopy [--backup-dir DIR]

The source is DATABASE_URL as written in skilltrack-api/.env (production), read over Neon's direct connection;
a DATABASE_URL set in the shell is ignored. The table structure is read from production itself, so the copy matches
it exactly, including columns added by migrate_db.py. The target must be empty and must not be the production host.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from _guard import host_of, production_url

from sqlalchemy import MetaData, create_engine, select, text  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--target", required=True, help="empty TEST database to copy into")
parser.add_argument("--backup-dir", help="also save every table as JSON in this folder (it contains password hashes)")
args = parser.parse_args()

SOURCE_URL = production_url() or exit("No DATABASE_URL found in skilltrack-api/.env.")
if host_of(args.target) == host_of(SOURCE_URL):
    raise SystemExit("Refusing to copy INTO the production database.")

source = create_engine(SOURCE_URL.replace("postgresql://", "postgresql+psycopg://", 1).replace("-pooler.", ".", 1))
target = create_engine(args.target.replace("postgresql://", "postgresql+psycopg://", 1))
meta = MetaData()
meta.reflect(source)
meta.create_all(target)

backup, counts = {}, {}
with source.connect() as src, target.begin() as dst:
    for table in meta.sorted_tables:
        rows = [dict(r._mapping) for r in src.execute(select(table))]
        if rows:
            dst.execute(table.insert(), rows)
        if "id" in table.c:
            dst.execute(text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                             f"COALESCE((SELECT MAX(id) FROM {table.name}), 1))"))
        backup[table.name], counts[table.name] = rows, len(rows)

with target.connect() as dst:
    copied = {t.name: dst.execute(text(f'SELECT count(*) FROM "{t.name}"')).scalar() for t in meta.sorted_tables}
print(f"copied {len(meta.sorted_tables)} tables, {sum(counts.values())} rows; counts match: {copied == counts}")
if args.backup_dir:
    out = Path(args.backup_dir) / f"db_backup_{datetime.now():%Y%m%d_%H%M}.json"
    out.write_text(json.dumps(backup, default=str, indent=1), encoding="utf-8")
    print("JSON backup:", out)
