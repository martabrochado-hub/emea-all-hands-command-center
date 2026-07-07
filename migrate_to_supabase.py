"""
One-time migration: copies all data from local SQLite → Supabase (PostgreSQL).

Usage:
    SUPABASE_DB_URL="postgresql://..." python3 migrate_to_supabase.py
"""

import json
import os
import sqlite3
import sys
import psycopg2
import psycopg2.extras

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "allhands.db")
_JSON_FIELDS = {"checklist", "prep_checklist", "ops_checklist", "reminders", "new_joiners_data"}


def sqlite_conn():
    c = sqlite3.connect(SQLITE_PATH)
    c.row_factory = sqlite3.Row
    return c


def pg_conn(url):
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def migrate(pg_url: str):
    src = sqlite_conn()
    dst = pg_conn(pg_url)

    # ── events ─────────────────────────────────────────────────
    events = [dict(r) for r in src.execute("SELECT * FROM events").fetchall()]
    print(f"Migrating {len(events)} events…")
    with dst.cursor() as cur:
        for ev in events:
            cols = list(ev.keys())
            vals = []
            for k, v in ev.items():
                # Re-encode JSON fields so they're valid JSON strings in Postgres
                if k in _JSON_FIELDS and v:
                    try:
                        json.loads(v)   # already valid JSON string
                        vals.append(v)
                    except Exception:
                        vals.append("[]")
                else:
                    vals.append(v if v is not None else "")
            phs = ", ".join(["%s"] * len(cols))
            col_str = ", ".join(cols)
            cur.execute(
                f"INSERT INTO events ({col_str}) VALUES ({phs}) ON CONFLICT (cycle) DO NOTHING",
                vals,
            )
    dst.commit()
    print("  ✓ events done")

    # ── contributors ───────────────────────────────────────────
    contribs = [dict(r) for r in src.execute("SELECT * FROM contributors").fetchall()]
    print(f"Migrating {len(contribs)} contributors…")
    with dst.cursor() as cur:
        for c in contribs:
            cols = [k for k in c.keys() if k != "id"]   # let SERIAL assign new IDs
            vals = [c[k] if c[k] is not None else "" for k in cols]
            phs  = ", ".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO contributors ({', '.join(cols)}) VALUES ({phs})", vals
            )
    dst.commit()
    print("  ✓ contributors done")

    # ── status_log ─────────────────────────────────────────────
    logs = [dict(r) for r in src.execute("SELECT * FROM status_log").fetchall()]
    print(f"Migrating {len(logs)} log entries…")
    with dst.cursor() as cur:
        for lg in logs:
            cols = [k for k in lg.keys() if k != "id"]
            vals = [lg[k] if lg[k] is not None else "" for k in cols]
            phs  = ", ".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO status_log ({', '.join(cols)}) VALUES ({phs})", vals
            )
    dst.commit()
    print("  ✓ status_log done")

    src.close()
    dst.close()
    print("\nMigration complete ✅")


if __name__ == "__main__":
    url = os.environ.get("SUPABASE_DB_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not url:
        print("Usage: SUPABASE_DB_URL='postgresql://...' python3 migrate_to_supabase.py")
        sys.exit(1)
    migrate(url)
