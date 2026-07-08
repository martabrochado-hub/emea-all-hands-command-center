"""
PostgreSQL persistence via Supabase — events, contributors, and status log.
Connection string read from st.secrets["SUPABASE_DB_URL"].
"""

import json
import psycopg2
import psycopg2.extras
import streamlit as st
from typing import Optional, List

DEFAULT_PREP_CHECKLIST = [
    {"id": "copy_presentation", "task": "Copy and save the last All Hands presentation", "status": "not_started", "owner": "", "notes": ""},
    {"id": "save_folder", "task": "Save the copy in a new folder (YYYY-MM)", "status": "not_started", "owner": "", "notes": ""},
    {"id": "confirm_contributors", "task": "Confirm contributors", "status": "not_started", "owner": "", "notes": ""},
    {"id": "track_confirmations", "task": "Track whether contributors are confirmed", "status": "not_started", "owner": "", "notes": ""},
    {"id": "create_slack_channel", "task": "Create internal Slack contributor channel", "status": "not_started", "owner": "", "notes": ""},
    {"id": "share_onboarding", "task": "Share the contributor onboarding message", "status": "not_started", "owner": "", "notes": ""},
    {"id": "attach_presentation", "task": "Attach or reference the presentation link", "status": "not_started", "owner": "", "notes": ""},
]

DEFAULT_OPS_CHECKLIST = [
    {"id": "post_reminder", "task": "Post reminder in emea-all-hands Slack channel", "phase": "day_of", "status": "not_started", "notes": ""},
    {"id": "confirm_zoom", "task": "Confirm Zoom link is correct", "phase": "day_of", "status": "not_started", "notes": ""},
    {"id": "confirm_presentation", "task": "Confirm presentation is finalized", "phase": "day_of", "status": "not_started", "notes": ""},
    {"id": "confirm_presenters", "task": "Confirm presenters are ready", "phase": "day_of", "status": "not_started", "notes": ""},
    {"id": "update_recordings", "task": "Update the EMEA All Hands Recordings folder", "phase": "post_event", "status": "not_started", "notes": ""},
    {"id": "create_feedback", "task": "Create the feedback form if not already created", "phase": "post_event", "status": "not_started", "notes": ""},
    {"id": "store_form", "task": "Store the form in the folder", "phase": "post_event", "status": "not_started", "notes": ""},
    {"id": "post_followup", "task": "Post the follow-up message in emea-channel", "phase": "post_event", "status": "not_started", "notes": ""},
]

_JSON_FIELDS = {"checklist", "prep_checklist", "ops_checklist", "reminders", "new_joiners_data"}


@st.cache_resource
def _get_connection() -> psycopg2.extensions.connection:
    """Cached connection reused across reruns — avoids per-request cold starts."""
    url = st.secrets["SUPABASE_DB_URL"]
    # Use Neon's pooler endpoint: keeps connections warm, eliminates scale-to-zero latency
    pooler_url = url.replace(
        "ep-noisy-hill-asr9uqsm.c-4.",
        "ep-noisy-hill-asr9uqsm-pooler.c-4.",
    )
    conn = psycopg2.connect(
        pooler_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
    )
    conn.autocommit = False
    return conn


def _conn() -> psycopg2.extensions.connection:
    conn = _get_connection()
    if conn.closed:
        _get_connection.clear()
        conn = _get_connection()
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        _get_connection.clear()
        conn = _get_connection()
    return conn


def init_db():
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    cycle                       TEXT PRIMARY KEY,
                    event_date                  TEXT DEFAULT '',
                    event_time                  TEXT DEFAULT '12pm',
                    uk_time                     TEXT DEFAULT '11am',
                    zoom_link                   TEXT DEFAULT '',
                    recording_link              TEXT DEFAULT '',
                    recording_passcode          TEXT DEFAULT '',
                    feedback_survey_link        TEXT DEFAULT '',
                    presentation_title          TEXT DEFAULT '',
                    presentation_link           TEXT DEFAULT '',
                    emea_folder_link            TEXT DEFAULT '',
                    emea_recordings_folder_link TEXT DEFAULT '',
                    contributor_deadline        TEXT DEFAULT '',
                    internal_owners             TEXT DEFAULT 'Marta Brochado, Klaudyna Bajkowska',
                    support_contacts            TEXT DEFAULT 'Rolando Angelini, Wojtek Szambelan',
                    prep_checklist              TEXT DEFAULT '[]',
                    ops_checklist               TEXT DEFAULT '[]',
                    zoom_passcode               TEXT DEFAULT '',
                    location                    TEXT DEFAULT '',
                    presentation_url            TEXT DEFAULT '',
                    parent_folder_url           TEXT DEFAULT '',
                    source_deck_url             TEXT DEFAULT '',
                    new_folder_name             TEXT DEFAULT '',
                    new_folder_id               TEXT DEFAULT '',
                    new_folder_url              TEXT DEFAULT '',
                    new_deck_url                TEXT DEFAULT '',
                    blank_deck_url              TEXT DEFAULT '',
                    recording_url               TEXT DEFAULT '',
                    feedback_url                TEXT DEFAULT '',
                    survey_url                  TEXT DEFAULT '',
                    slack_channel_id            TEXT DEFAULT '',
                    slack_channel_name          TEXT DEFAULT '',
                    checklist                   TEXT DEFAULT '{}',
                    reminders                   TEXT DEFAULT '[]',
                    contributor_msg_final       TEXT DEFAULT '',
                    post_event_channel          TEXT DEFAULT 'online-monthly-emea-all-hands',
                    post_event_scheduled_date   TEXT DEFAULT '',
                    post_event_scheduled_time   TEXT DEFAULT '17:00',
                    post_event_msg_final        TEXT DEFAULT '',
                    post_event_status           TEXT DEFAULT 'pending',
                    contributor_msg_status      TEXT DEFAULT '',
                    notion_saved                INTEGER DEFAULT 0,
                    new_joiners_start_date      TEXT DEFAULT '',
                    new_joiners_end_date        TEXT DEFAULT '',
                    new_joiners_data            TEXT DEFAULT '[]',
                    new_joiners_slide_updated   INTEGER DEFAULT 0,
                    new_joiners_fetching        INTEGER DEFAULT 0,
                    created_at                  TEXT DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS contributors (
                    id                      SERIAL PRIMARY KEY,
                    cycle                   TEXT NOT NULL,
                    name                    TEXT NOT NULL,
                    email                   TEXT DEFAULT '',
                    slack_id                TEXT DEFAULT '',
                    team_function           TEXT DEFAULT '',
                    topic                   TEXT DEFAULT '',
                    availability_confirmed  INTEGER DEFAULT 0,
                    presentation_confirmed  INTEGER DEFAULT 0,
                    slack_channel_created   INTEGER DEFAULT 0,
                    notes                   TEXT DEFAULT '',
                    confirmed               INTEGER DEFAULT 0,
                    FOREIGN KEY (cycle) REFERENCES events(cycle) ON DELETE CASCADE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS status_log (
                    id      SERIAL PRIMARY KEY,
                    cycle   TEXT NOT NULL,
                    ts      TEXT DEFAULT '',
                    icon    TEXT DEFAULT '🔵',
                    message TEXT NOT NULL,
                    FOREIGN KEY (cycle) REFERENCES events(cycle) ON DELETE CASCADE
                )
            """)
            # Add any new columns that may not exist yet
            new_columns = [
                ("events", "reminders",                 "TEXT DEFAULT '[]'"),
                ("events", "contributor_msg_final",     "TEXT DEFAULT ''"),
                ("events", "post_event_channel",        "TEXT DEFAULT 'online-monthly-emea-all-hands'"),
                ("events", "post_event_scheduled_date", "TEXT DEFAULT ''"),
                ("events", "post_event_scheduled_time", "TEXT DEFAULT '17:00'"),
                ("events", "post_event_msg_final",      "TEXT DEFAULT ''"),
                ("events", "post_event_status",         "TEXT DEFAULT 'pending'"),
                ("events", "contributor_msg_status",    "TEXT DEFAULT ''"),
                ("events", "notion_saved",              "INTEGER DEFAULT 0"),
                ("events", "new_joiners_start_date",    "TEXT DEFAULT ''"),
                ("events", "new_joiners_end_date",      "TEXT DEFAULT ''"),
                ("events", "new_joiners_data",          "TEXT DEFAULT '[]'"),
                ("events", "new_joiners_slide_updated", "INTEGER DEFAULT 0"),
                ("events", "new_joiners_fetching",      "INTEGER DEFAULT 0"),
                ("contributors", "team_function",           "TEXT DEFAULT ''"),
                ("contributors", "availability_confirmed",  "INTEGER DEFAULT 0"),
                ("contributors", "presentation_confirmed",  "INTEGER DEFAULT 0"),
                ("contributors", "slack_channel_created",   "INTEGER DEFAULT 0"),
                ("contributors", "notes",                   "TEXT DEFAULT ''"),
            ]
            for table, col, col_def in new_columns:
                cur.execute(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}"
                )
        conn.commit()
    finally:
        conn.close()


# ── Events ─────────────────────────────────────────────────────

def get_event(cycle: str) -> Optional[dict]:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM events WHERE cycle = %s", (cycle,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    d = dict(row)
    for f in _JSON_FIELDS:
        raw = d.get(f)
        d[f] = json.loads(raw) if raw else ([] if f != "checklist" else {})
    return d


def upsert_event(cycle: str, **fields):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM events WHERE cycle = %s", (cycle,))
            exists = cur.fetchone()
            if exists:
                parts, vals = [], []
                for k, v in fields.items():
                    parts.append(f"{k} = %s")
                    vals.append(json.dumps(v) if k in _JSON_FIELDS else v)
                if parts:
                    vals.append(cycle)
                    cur.execute(
                        f"UPDATE events SET {', '.join(parts)} WHERE cycle = %s", vals
                    )
            else:
                if "prep_checklist" not in fields:
                    fields["prep_checklist"] = DEFAULT_PREP_CHECKLIST
                if "ops_checklist" not in fields:
                    fields["ops_checklist"] = DEFAULT_OPS_CHECKLIST
                cols, phs, vals = ["cycle"], ["%s"], [cycle]
                for k, v in fields.items():
                    cols.append(k)
                    phs.append("%s")
                    vals.append(json.dumps(v) if k in _JSON_FIELDS else v)
                cur.execute(
                    f"INSERT INTO events ({', '.join(cols)}) VALUES ({', '.join(phs)})",
                    vals,
                )
        conn.commit()
    finally:
        conn.close()


def set_check(cycle: str, key: str, val: bool):
    ev = get_event(cycle)
    if not ev:
        return
    cl = ev.get("checklist", {})
    cl[key] = val
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE events SET checklist = %s WHERE cycle = %s",
                (json.dumps(cl), cycle),
            )
        conn.commit()
    finally:
        conn.close()


def delete_event(cycle: str):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM status_log   WHERE cycle = %s", (cycle,))
            cur.execute("DELETE FROM contributors WHERE cycle = %s", (cycle,))
            cur.execute("DELETE FROM events       WHERE cycle = %s", (cycle,))
        conn.commit()
    finally:
        conn.close()


def list_cycles() -> List[str]:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cycle FROM events "
                "ORDER BY CASE WHEN event_date != '' THEN event_date ELSE cycle END DESC"
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [r["cycle"] for r in rows]


# ── Contributors ───────────────────────────────────────────────

def get_contributors(cycle: str) -> List[dict]:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM contributors WHERE cycle = %s ORDER BY name", (cycle,)
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def add_contributor(cycle: str, name: str, **kwargs):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cols = ["cycle", "name"]
            vals = [cycle, name]
            for k, v in kwargs.items():
                cols.append(k)
                vals.append(v)
            phs = ", ".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO contributors ({', '.join(cols)}) VALUES ({phs})", vals
            )
        conn.commit()
    finally:
        conn.close()


def update_contributor(cid: int, **fields):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            parts, vals = [], []
            for k, v in fields.items():
                parts.append(f"{k} = %s")
                vals.append(v)
            if parts:
                vals.append(cid)
                cur.execute(
                    f"UPDATE contributors SET {', '.join(parts)} WHERE id = %s", vals
                )
        conn.commit()
    finally:
        conn.close()


def delete_contributor(cid: int):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contributors WHERE id = %s", (cid,))
        conn.commit()
    finally:
        conn.close()


# ── Status Log ─────────────────────────────────────────────────

def log(cycle: str, message: str, icon: str = "🔵"):
    from datetime import datetime
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO status_log (cycle, ts, icon, message) VALUES (%s, %s, %s, %s)",
                (cycle, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), icon, message),
            )
        conn.commit()
    finally:
        conn.close()


def get_logs(cycle: str, limit: int = 50) -> List[dict]:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM status_log WHERE cycle = %s ORDER BY id DESC LIMIT %s",
                (cycle, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


init_db()
