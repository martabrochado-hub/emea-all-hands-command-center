"""
Affirm EMEA All Hands — Command Center
Streamlit app for the People Team to manage the full All Hands lifecycle.
"""

import streamlit as st
from datetime import datetime, date
import json
import copy
import re
import os

_AUTO_TITLE_RE = re.compile(r'^\d{6,8}_EMEA AllHands$')

import db
import templates
import exports
import slack_ops
import drive

# ── Fixed defaults ───────────────────────────────────────────────
DEFAULT_ZOOM           = "https://affirm.zoom.us/j/99928744647"
EMEA_PARENT_FOLDER_ID = "1OHnR9AvDGPbQ3TeB_Ogjug-mffy8yTIT"

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

LIGHT_INDIGO = "#9DADF9"
INDIGO = "#4A4AF4"
DARK_INDIGO = "#0A0340"
WHITE = "#FFFFFF"
AFFIRM_BLACK = "#13131F"
CARD_BG = "#1B1B2F"
SURFACE = "#15151F"
BORDER = "#2A2A3D"
TEXT_1 = "#F0F0F5"
TEXT_2 = "#A0A0B8"
SUCCESS = "#34D399"
WARNING = "#FBBF24"
DANGER = "#F87171"

STATUS_OPTIONS = ["Not started", "In progress", "Done", "Blocked"]
STATUS_MAP = {
    "Not started": "not_started",
    "In progress": "in_progress",
    "Done": "done",
    "Blocked": "blocked",
}
STATUS_REVERSE = {v: k for k, v in STATUS_MAP.items()}

NAV_ITEMS = [
    "📋  Event Setup",
    "👥  Contributors",
    "💬  Communications",
    "🆕  New Joiners",
    "⏰  Auto Reminders",
    "📮  Post Event",
    "📒  Notion Folder",
]

COUNTRY_FLAGS = {
    "united kingdom": "🇬🇧", "uk": "🇬🇧", "england": "🇬🇧", "scotland": "🇬🇧",
    "london": "🇬🇧", "manchester": "🇬🇧", "edinburgh": "🇬🇧", "birmingham": "🇬🇧",
    "spain": "🇪🇸", "madrid": "🇪🇸", "barcelona": "🇪🇸", "seville": "🇪🇸",
    "sevilla": "🇪🇸", "valencia": "🇪🇸", "bilbao": "🇪🇸",
    "france": "🇫🇷", "paris": "🇫🇷", "lyon": "🇫🇷", "marseille": "🇫🇷",
    "germany": "🇩🇪", "berlin": "🇩🇪", "munich": "🇩🇪", "münchen": "🇩🇪",
    "hamburg": "🇩🇪", "frankfurt": "🇩🇪", "cologne": "🇩🇪",
    "netherlands": "🇳🇱", "amsterdam": "🇳🇱", "rotterdam": "🇳🇱",
    "poland": "🇵🇱", "warsaw": "🇵🇱", "krakow": "🇵🇱", "wroclaw": "🇵🇱",
    "gdansk": "🇵🇱", "poznań": "🇵🇱",
    "sweden": "🇸🇪", "stockholm": "🇸🇪", "gothenburg": "🇸🇪",
    "norway": "🇳🇴", "oslo": "🇳🇴",
    "denmark": "🇩🇰", "copenhagen": "🇩🇰",
    "finland": "🇫🇮", "helsinki": "🇫🇮",
    "italy": "🇮🇹", "rome": "🇮🇹", "milan": "🇮🇹",
    "portugal": "🇵🇹", "lisbon": "🇵🇹", "porto": "🇵🇹",
    "ireland": "🇮🇪", "dublin": "🇮🇪",
    "australia": "🇦🇺", "sydney": "🇦🇺", "melbourne": "🇦🇺",
    "canada": "🇨🇦", "toronto": "🇨🇦", "vancouver": "🇨🇦",
    "singapore": "🇸🇬",
    "india": "🇮🇳", "bangalore": "🇮🇳", "bengaluru": "🇮🇳", "mumbai": "🇮🇳",
    "israel": "🇮🇱", "tel aviv": "🇮🇱",
    "united states": "🇺🇸", "usa": "🇺🇸", "new york": "🇺🇸", "san francisco": "🇺🇸",
}

NOTION_PAGE_URL = "https://app.notion.com/p/affirm/EMEA-All-Hands-10d40e54ae38807eb40fd687c7f7a306"


# ═══════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(
        f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        .stApp {{
            background: {AFFIRM_BLACK};
            font-family: 'Axiforma', 'Inter', Arial, sans-serif;
        }}
        header[data-testid="stHeader"] {{ background: {DARK_INDIGO} !important; }}
        section[data-testid="stSidebar"] {{
            background: {SURFACE} !important;
            border-right: 1px solid {BORDER};
        }}

        /* Cards */
        .card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
        }}
        .card h4 {{ color: {TEXT_1}; margin-top: 0; font-weight: 700; }}
        .card p  {{ color: {TEXT_2}; font-size: .88rem; }}

        /* Section header */
        .section-hdr {{
            font-size: 1.35rem;
            font-weight: 700;
            color: {TEXT_1};
            padding-bottom: 10px;
            border-bottom: 3px solid {INDIGO};
            margin-bottom: 24px;
        }}
        .sub-hdr {{
            font-size: 1.05rem;
            font-weight: 600;
            color: {LIGHT_INDIGO};
            margin: 20px 0 12px;
        }}

        /* Badges */
        .b {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: .75rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        .b-ok      {{ background: #10b98122; color: {SUCCESS}; border: 1px solid #10b98144; }}
        .b-warn    {{ background: #f59e0b22; color: {WARNING}; border: 1px solid #f59e0b44; }}
        .b-err     {{ background: #ef444422; color: {DANGER};  border: 1px solid #ef444444; }}
        .b-info    {{ background: {INDIGO}22; color: {LIGHT_INDIGO}; border: 1px solid {INDIGO}44; }}
        .b-default {{ background: #64748b22; color: #94A3B8; border: 1px solid #64748b44; }}

        /* Progress bar */
        .pbar  {{ background: {SURFACE}; border-radius: 8px; height: 12px; overflow: hidden; border: 1px solid {BORDER}; }}
        .pfill {{ height: 100%; border-radius: 8px; transition: width .4s; }}

        /* Message card */
        .msg-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
        }}
        .msg-card h4 {{ color: {TEXT_1}; margin: 0 0 4px; font-weight: 700; font-size: 1.05rem; }}
        .msg-card .desc {{ color: {TEXT_2}; font-size: .82rem; margin-bottom: 14px; }}

        /* Smart helper alert */
        .smart-alert {{
            background: {INDIGO}15;
            border: 1px solid {INDIGO}44;
            border-radius: 12px;
            padding: 14px 18px;
            margin-bottom: 16px;
            color: {LIGHT_INDIGO};
            font-size: .88rem;
        }}

        /* Checklist header row */
        .cl-hdr {{
            display: flex; gap: 8px; padding: 6px 0 10px;
            font-weight: 600; font-size: .82rem; color: {TEXT_2};
            border-bottom: 1px solid {BORDER};
            margin-bottom: 8px;
        }}

        /* Contributor table header */
        .ct-hdr {{
            display: grid;
            grid-template-columns: 2fr 1.5fr 1.5fr 1fr 1fr 1fr 2fr;
            gap: 8px; padding: 8px 0;
            font-weight: 600; font-size: .8rem; color: {TEXT_2};
            border-bottom: 1px solid {BORDER};
        }}

        /* Hide Streamlit defaults */
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        div[data-testid="stSidebar"] .stRadio label {{
            font-size: .92rem !important;
        }}
    </style>""",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def badge(text: str, variant: str = "info") -> str:
    return f'<span class="b b-{variant}">{text}</span>'


def progress_bar(pct: int):
    st.markdown(
        f'<div class="pbar"><div class="pfill" style="width:{pct}%;background:{SUCCESS};"></div></div>',
        unsafe_allow_html=True,
    )


def section_header(text: str):
    st.markdown(f'<div class="section-hdr">{text}</div>', unsafe_allow_html=True)


def sub_header(text: str):
    st.markdown(f'<div class="sub-hdr">{text}</div>', unsafe_allow_html=True)


def _get_flag(location: str) -> str:
    loc = location.lower()
    for keyword, flag in COUNTRY_FLAGS.items():
        if keyword in loc:
            return flag
    return "🌍"


def _clear_nj_session_state(cycle: str):
    for key in list(st.session_state.keys()):
        if key.startswith("nj_") and key.endswith(f"_{cycle}"):
            del st.session_state[key]


def _status_badge(status: str) -> str:
    variant = {
        "not_started": "default",
        "in_progress": "warn",
        "done": "ok",
        "blocked": "err",
    }.get(status, "default")
    label = status.replace("_", " ").title()
    return badge(label, variant)


def _fmt_cycle(cycle: str) -> str:
    """Format '2026-06' as 'June 2026' for the sidebar selector."""
    try:
        y, m = cycle.split("-")
        return datetime(int(y), int(m), 1).strftime("%B %Y")
    except Exception:
        return cycle


def _find_latest_presentation() -> str | None:
    """Return the file ID of the most recent EMEA All Hands presentation."""
    try:
        svc, err = drive._get_service("drive", "v3")
        if err:
            return None
        # list folders in parent, sorted newest first by name (YYYYMMDD)
        resp = svc.files().list(
            q=f"'{EMEA_PARENT_FOLDER_ID}' in parents and trashed = false"
              f" and mimeType = 'application/vnd.google-apps.folder'",
            fields="files(id, name)",
            orderBy="name desc",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=5,
        ).execute()
        for folder in resp.get("files", []):
            # look for a presentation inside this folder
            pr = svc.files().list(
                q=f"'{folder['id']}' in parents and trashed = false"
                  f" and mimeType = 'application/vnd.google-apps.presentation'",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1,
            ).execute()
            if pr.get("files"):
                return pr["files"][0]["id"]
    except Exception:
        pass
    return None


def _prev_cycle(current: str) -> str | None:
    """Return the most recent cycle in the DB that is earlier than `current`."""
    for c in sorted(db.list_cycles(), reverse=True):
        if c < current:
            return c
    return None


def _channel_and_pres_names(cycle: str, ev: dict) -> tuple[str, str]:
    """Return (channel_name, pres_name) using the event date if set, else the cycle month."""
    ev_date = ev.get("event_date", "") if ev else ""
    if ev_date:
        date_str = ev_date.replace("-", "")          # e.g. "20260623"
        channel_name = f"{date_str}_emea_all-hands"  # matches #20260427_emea_all-hands pattern
        pres_name    = f"{date_str}_EMEA AllHands"
    else:
        ym = cycle.replace("-", "")                  # e.g. "202606"
        channel_name = f"{ym}_emea_all-hands"
        pres_name    = f"{ym}_EMEA AllHands"
    return channel_name, pres_name


def compute_progress(event: dict, contributors: list) -> tuple[int, list[str]]:
    """Returns (pct, list of completed stage labels) based on the 6 workflow stages."""
    stages = [
        ("📋 Event Setup",       bool(event.get("event_date") and event.get("zoom_link"))),
        ("👥 Contributors",      len(contributors) > 0),
        ("💬 Communications",    bool(event.get("contributor_msg_final", "").strip())),
        ("🆕 New Joiners Slide", bool(event.get("new_joiners_slide_updated", False))),
        ("⏰ Auto Reminders",    any(
            r.get("status") == "approved"
            for r in event.get("reminders", [])
        )),
        ("📮 Post Event",        event.get("post_event_status") in ("approved", "sent")),
    ]
    done_stages = [label for label, done in stages if done]
    pct = int(len(done_stages) / len(stages) * 100)
    return pct, done_stages


def check_missing_fields(event: dict) -> list[str]:
    warnings = []
    if not event.get("presentation_link"):
        warnings.append("Presentation link missing")
    return warnings


def _ensure_checklists(cycle: str, ev: dict) -> dict:
    """Backfill default checklists if the event was created before the new schema."""
    changed = False
    if not ev.get("prep_checklist"):
        ev["prep_checklist"] = copy.deepcopy(db.DEFAULT_PREP_CHECKLIST)
        changed = True
    if not ev.get("ops_checklist"):
        ev["ops_checklist"] = copy.deepcopy(db.DEFAULT_OPS_CHECKLIST)
        changed = True
    if changed:
        db.upsert_event(
            cycle,
            prep_checklist=ev["prep_checklist"],
            ops_checklist=ev["ops_checklist"],
        )
    return ev


def _build_messages(ev: dict) -> dict:
    return {
        "contributor": templates.contributor_message(
            ev.get("presentation_title", ""),
            ev.get("presentation_link", ""),
            ev.get("support_contacts", "Rolando Angelini, Wojtek Szambelan"),
        ),
        "pre_event": templates.pre_event_reminder(
            ev.get("event_date", "TBD"),
            ev.get("event_time", "12pm"),
            ev.get("uk_time", "11am"),
            ev.get("zoom_link", ""),
        ),
        "post_event": templates.post_event_followup(
            ev.get("recording_link", ""),
            ev.get("recording_passcode", ""),
            ev.get("feedback_survey_link", ""),
        ),
    }


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════

def _month_opts() -> tuple[list[str], str]:
    """Return (options, default_cycle) for the month selector."""
    now = datetime.now()
    months = []
    for d in range(-2, 7):
        m = now.month + d
        y = now.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        months.append(f"{y}-{m:02d}")
    existing = db.list_cycles()
    opts = sorted(set(months + existing), reverse=True)
    default = f"{now.year}-{now.month:02d}"
    return opts, default


def render_sidebar(cycle: str) -> str:
    """Sidebar for an open event. Returns selected section."""
    with st.sidebar:
        st.markdown(
            f"""<div style="text-align:center;padding:12px 0 8px;">
                <span style="font-size:1.8rem;font-weight:800;color:{INDIGO};">EMEA</span><br>
                <span style="font-size:.72rem;color:{TEXT_2};letter-spacing:3px;font-weight:500;">
                    ALL HANDS COMMAND CENTER
                </span>
            </div>""",
            unsafe_allow_html=True,
        )

        if st.button("← All Events", use_container_width=True):
            st.session_state.pop("current_cycle", None)
            st.rerun()

        st.divider()

        ev = db.get_event(cycle)
        ev_date_display = cycle
        try:
            ev_date_display = datetime.strptime(ev["event_date"], "%Y-%m-%d").strftime("%-d %b %Y")
        except Exception:
            pass
        st.markdown(
            f'<div style="text-align:center;padding:4px 0 10px;">'
            f'<span style="font-size:1rem;font-weight:700;color:{TEXT_1};">📅 {ev_date_display}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        contribs = db.get_contributors(cycle)
        pct, done_stages = compute_progress(ev, contribs)
        st.caption(f"Progress — {len(done_stages)}/6 stages")
        progress_bar(pct)

        st.divider()
        # Apply programmatic navigation (set before widget renders so it takes effect)
        if "_nav_goto" in st.session_state:
            st.session_state["_nav_radio"] = NAV_ITEMS[st.session_state.pop("_nav_goto")]
        section = st.radio("Navigate", NAV_ITEMS, label_visibility="collapsed", key="_nav_radio")

        st.divider()
        if st.button("🗑 Reset this event", use_container_width=True):
            db.delete_event(cycle)
            st.session_state.pop("current_cycle", None)
            st.rerun()

        return section


def render_home():
    """Home page — lists all events and lets you create a new one."""
    # ── Header ─────────────────────────────────────────────────
    st.markdown(
        f"""<div style="text-align:center;padding:56px 0 32px;">
            <span style="font-size:2.8rem;font-weight:800;color:{INDIGO};">EMEA All Hands</span><br>
            <span style="color:{TEXT_2};font-size:.85rem;letter-spacing:3px;font-weight:500;
                         display:block;margin-top:8px;">COMMAND CENTER</span>
        </div>""",
        unsafe_allow_html=True,
    )

    cycles = db.list_cycles()
    active = [(c, db.get_event(c)) for c in cycles if db.get_event(c) and db.get_event(c).get("event_date")]

    # ── Recent events (2 most recent cards) ────────────────────
    recent = active[:2]
    if recent:
        sub_header("Your All Hands")
        cols = st.columns(len(recent))
        for i, (cycle, ev) in enumerate(recent):
            try:
                date_display = datetime.strptime(ev["event_date"], "%Y-%m-%d").strftime("%-d %b %Y")
                month_label  = datetime.strptime(ev["event_date"], "%Y-%m-%d").strftime("%B %Y")
            except Exception:
                date_display = ev["event_date"]
                month_label  = _fmt_cycle(cycle)
            with cols[i]:
                contribs = db.get_contributors(cycle)
                pct, _ = compute_progress(ev, contribs)
                st.markdown(
                    f'<div class="card" style="cursor:pointer;">'
                    f'<h4 style="margin-bottom:4px;">{month_label}</h4>'
                    f'<p style="margin:0 0 10px;">📅 {date_display}</p>'
                    f'<div class="pbar"><div class="pfill" style="width:{pct}%;background:{SUCCESS};"></div></div>'
                    f'<p style="font-size:.78rem;margin:6px 0 0;">{pct}%</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Open {month_label} →", key=f"open_{cycle}", use_container_width=True):
                    st.session_state["current_cycle"] = cycle
                    st.rerun()
        st.write("")

    # ── New event ───────────────────────────────────────────────
    st.divider()
    sub_header("Plan a New All Hands")
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.caption("When is the event?")
        ev_date = st.date_input("Event date", value=None, format="DD/MM/YYYY", label_visibility="collapsed")

        if ev_date:
            date_str = ev_date.strftime("%Y%m%d")
            st.markdown(
                f'<div class="smart-alert" style="margin:10px 0 6px;text-align:center;">'
                f'Channel: <strong>#{date_str}_emea_all-hands</strong></div>',
                unsafe_allow_html=True,
            )

        go = st.button("Start Planning →", type="primary", use_container_width=True, disabled=ev_date is None)
        if not ev_date:
            st.caption("Pick a date to continue")

    if go and ev_date:
        date_str  = ev_date.strftime("%Y%m%d")
        cycle     = f"{ev_date.year}-{ev_date.month:02d}"
        pres_name = f"{date_str}_EMEA AllHands"

        with st.spinner("Creating Drive folder and copying presentation…"):
            folder_url, pres_url = "", ""
            folder_res = drive.create_folder(EMEA_PARENT_FOLDER_ID, date_str)
            if folder_res.get("ok"):
                folder_url = folder_res["url"]
                src_id = _find_latest_presentation()
                if src_id:
                    pres_res = drive.copy_presentation(src_id, folder_res["folder_id"], pres_name)
                    if pres_res.get("ok"):
                        pres_url = pres_res["url"]

        db.upsert_event(
            cycle,
            event_date        = str(ev_date),
            zoom_link         = DEFAULT_ZOOM,
            emea_folder_link  = folder_url,
            presentation_link = pres_url,
            presentation_title= pres_name,
        )
        db.log(cycle, f"Event created — {ev_date}", "🆕")
        st.session_state["current_cycle"] = cycle
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# SECTION 1 — EVENT SETUP
# ═══════════════════════════════════════════════════════════════

def render_event_setup(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first using the sidebar.")
        return

    section_header("📋 Event Setup")

    warnings = check_missing_fields(ev)
    if warnings:
        st.markdown(
            f'<div class="smart-alert">⚠️ <strong>{len(warnings)} field{"s" if len(warnings) != 1 else ""}'
            f" need attention:</strong> " + ", ".join(warnings) + "</div>",
            unsafe_allow_html=True,
        )

    # ── Event date — outside the form so sidebar updates immediately ──
    ev_date_val = date.today()
    if ev.get("event_date"):
        try:
            ev_date_val = datetime.strptime(ev["event_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    sub_header("Core Details")
    ev_date = st.date_input("Event date", value=ev_date_val, key="ev_date_picker")

    # Immediately save whenever the date changes — keeps sidebar + Drive in sync
    if str(ev_date) != ev.get("event_date", ""):
        new_ds = str(ev_date).replace("-", "")
        old_t  = ev.get("presentation_title", "")
        new_t  = f"{new_ds}_EMEA AllHands" if (not old_t or _AUTO_TITLE_RE.match(old_t)) else old_t
        old_ds = old_t[:8] if (old_t and _AUTO_TITLE_RE.match(old_t)) else ""
        date_changed = bool(old_ds and old_ds != new_ds)

        update = {"event_date": str(ev_date), "presentation_title": new_t}

        if date_changed:
            # Create the new Drive folder immediately so the link is never "missing"
            with st.spinner(f"Creating Drive folder {new_ds}…"):
                folder_res = drive.create_folder(EMEA_PARENT_FOLDER_ID, new_ds)
                if folder_res.get("ok"):
                    update["emea_folder_link"] = folder_res["url"]
                    src_id = _find_latest_presentation()
                    if src_id:
                        pres_res = drive.copy_presentation(src_id, folder_res["folder_id"], new_t)
                        if pres_res.get("ok"):
                            update["presentation_link"] = pres_res["url"]

        db.upsert_event(cycle, **update)
        st.rerun()

    channel_name, pres_name = _channel_and_pres_names(cycle, ev)

    with st.form("event_setup_form"):
        c1, c2 = st.columns(2)
        ev_time = c1.text_input("Event time", value=ev.get("event_time", "12pm"))

        c3, c4 = st.columns(2)
        uk_time = c3.text_input("UK time equivalent", value=ev.get("uk_time", "11am"))
        zoom_link = c4.text_input("Zoom link", value=ev.get("zoom_link") or DEFAULT_ZOOM)

        sub_header("Presentation")
        saved_title = ev.get("presentation_title", "")
        default_title = pres_name if (not saved_title or _AUTO_TITLE_RE.match(saved_title)) else saved_title
        # Presentation link is auto-managed — show as read-only reference, pass through on save
        presentation_link = ev.get("presentation_link", "")

        sub_header("People & Deadlines")
        c11, c12 = st.columns(2)
        deadline_val = date.today()
        if ev.get("contributor_deadline"):
            try:
                deadline_val = datetime.strptime(ev["contributor_deadline"], "%Y-%m-%d").date()
            except ValueError:
                pass
        contributor_deadline = c11.date_input("Contributor deadline", value=deadline_val)
        c12.write("")  # spacer

        c13, c14 = st.columns(2)
        internal_owners = c13.text_input(
            "Internal owners",
            value=ev.get("internal_owners", "Marta Brochado, Klaudyna Bajkowska"),
        )
        support_contacts = c14.text_input(
            "Support contacts",
            value=ev.get("support_contacts", "Rolando Angelini, Wojtek Szambelan"),
        )

        submitted = st.form_submit_button("Save Event Details", type="primary", use_container_width=True)

    # Show presentation as a read-only clickable link (auto-managed, not editable)
    pres_url = ev.get("presentation_link", "")
    if pres_url:
        st.markdown(
            f'<div class="smart-alert">📊 Presentation: '
            f'<a href="{pres_url}" target="_blank" style="color:{LIGHT_INDIGO};">'
            f'{ev.get("presentation_title", "Open →")}</a></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("📊 Presentation link will appear here once the Drive folder is created.")

    if submitted:
        # Auto-title always tracks the event date; only preserve a custom title
        old_title = ev.get("presentation_title", "")
        new_date_str = str(ev_date).replace("-", "")
        final_title = (
            f"{new_date_str}_EMEA AllHands"
            if (not old_title or _AUTO_TITLE_RE.match(old_title))
            else old_title
        )
        db.upsert_event(
            cycle,
            event_date=str(ev_date),
            event_time=ev_time,
            uk_time=uk_time,
            zoom_link=zoom_link,
            presentation_title=final_title,
            presentation_link=presentation_link,
            contributor_deadline=str(contributor_deadline),
            internal_owners=internal_owners,
            support_contacts=support_contacts,
        )

        # Drive setup: create folder once, then only fill presentation if still missing.
        ev_now = db.get_event(cycle)
        folder_link = ev_now.get("emea_folder_link", "")
        pres_link   = ev_now.get("presentation_link", "")

        if not folder_link:
            # Brand-new event — create folder + copy presentation
            with st.spinner("Creating Drive folder…"):
                folder_res = drive.create_folder(EMEA_PARENT_FOLDER_ID, new_date_str)
                if folder_res.get("ok"):
                    folder_link = folder_res["url"]
                    db.upsert_event(cycle, emea_folder_link=folder_link)
                    src_id = _find_latest_presentation()
                    if src_id:
                        pres_res = drive.copy_presentation(src_id, folder_res["folder_id"], final_title)
                        if pres_res.get("ok"):
                            db.upsert_event(cycle, presentation_link=pres_res["url"], presentation_title=final_title)
        elif not pres_link:
            # Folder exists but presentation link is missing — find it in the existing folder
            with st.spinner("Looking for presentation in existing folder…"):
                folder_id = drive.extract_file_id(folder_link)
                try:
                    svc, _ = drive._get_service("drive", "v3")
                    if svc:
                        resp = svc.files().list(
                            q=f"'{folder_id}' in parents and trashed = false"
                              f" and mimeType = 'application/vnd.google-apps.presentation'",
                            fields="files(id, name)",
                            supportsAllDrives=True, includeItemsFromAllDrives=True,
                        ).execute()
                        files = resp.get("files", [])
                        if files:
                            pres_url = f"https://docs.google.com/presentation/d/{files[0]['id']}/edit"
                            db.upsert_event(cycle, presentation_link=pres_url)
                        else:
                            # No presentation yet — copy one in
                            src_id = _find_latest_presentation()
                            if src_id:
                                pres_res = drive.copy_presentation(src_id, folder_id, final_title)
                                if pres_res.get("ok"):
                                    db.upsert_event(cycle, presentation_link=pres_res["url"])
                except Exception:
                    pass

        db.log(cycle, "Event details saved", "✅")
        st.toast("Event details saved!", icon="✅")
        st.session_state["_nav_goto"] = 1  # advance to Contributors
        st.rerun()



# ═══════════════════════════════════════════════════════════════
# SECTION 2 — PREPARATION CHECKLIST
# ═══════════════════════════════════════════════════════════════

def render_prep_checklist(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return
    ev = _ensure_checklists(cycle, ev)

    section_header("✅ Internal Preparation Checklist")

    prep = ev.get("prep_checklist", [])
    done_count = sum(1 for i in prep if i.get("status") == "done")
    st.markdown(
        f"**{done_count}/{len(prep)}** tasks completed  "
        + _status_badge("done" if done_count == len(prep) else "in_progress"),
        unsafe_allow_html=True,
    )
    st.write("")

    with st.form("prep_form"):
        for i, item in enumerate(prep):
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 2, 2])
            current_status = STATUS_REVERSE.get(item.get("status", "not_started"), "Not started")
            c1.selectbox(
                f"s_{i}",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current_status),
                key=f"prep_s_{i}",
                label_visibility="collapsed",
            )
            c2.text_input(f"t_{i}", value=item["task"], disabled=True, key=f"prep_t_{i}", label_visibility="collapsed")
            c3.text_input(
                f"o_{i}",
                value=item.get("owner", ""),
                placeholder="Owner",
                key=f"prep_o_{i}",
                label_visibility="collapsed",
            )
            c4.text_input(
                f"n_{i}",
                value=item.get("notes", ""),
                placeholder="Notes",
                key=f"prep_n_{i}",
                label_visibility="collapsed",
            )

        save = st.form_submit_button("Save Checklist", type="primary", use_container_width=True)

    if save:
        updated = []
        for i, item in enumerate(prep):
            updated.append({
                **item,
                "status": STATUS_MAP.get(st.session_state[f"prep_s_{i}"], "not_started"),
                "owner": st.session_state[f"prep_o_{i}"],
                "notes": st.session_state[f"prep_n_{i}"],
            })
        db.upsert_event(cycle, prep_checklist=updated)
        db.log(cycle, "Preparation checklist updated", "✅")
        st.toast("Checklist saved!", icon="✅")
        st.rerun()



# ═══════════════════════════════════════════════════════════════
# SECTION 3 — CONTRIBUTOR TRACKER
# ═══════════════════════════════════════════════════════════════

def render_contributors(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("👥 Contributors")

    # ── Slack channel banner ────────────────────────────────────
    channel_name, _ = _channel_and_pres_names(cycle, ev)
    existing_ch_id   = ev.get("slack_channel_id", "")
    existing_ch_name = ev.get("slack_channel_name", "")

    if existing_ch_id:
        st.markdown(
            f'<div class="smart-alert">💬 Contributor channel: <strong>#{existing_ch_name}</strong></div>',
            unsafe_allow_html=True,
        )
    else:
        sc1, sc2 = st.columns([3, 1])
        sc1.markdown(
            f'<div style="color:{TEXT_2};font-size:.88rem;padding-top:8px;">'
            f'Create the private contributor channel: <strong style="color:{TEXT_1};">#{channel_name}</strong></div>',
            unsafe_allow_html=True,
        )
        slack_ready = slack_ops.is_token_configured()
        if sc2.button("🚀 Create Channel", disabled=not slack_ready, use_container_width=True):
            result = slack_ops.create_channel(channel_name, is_private=True)
            if result.get("ok"):
                db.upsert_event(cycle, slack_channel_id=result["channel_id"], slack_channel_name=result["channel_name"])
                db.log(cycle, f"Slack channel created: #{result['channel_name']}", "💬")
                st.toast(f"#{result['channel_name']} created!", icon="💬")
                st.rerun()
            else:
                st.error(f"Slack error: {result.get('error')}")

    st.divider()

    # ── Load Slack user cache for autocomplete ──────────────────
    import json as _json
    _cache_path = os.path.join(os.path.dirname(__file__), "slack_users_cache.json")
    if "slack_users" not in st.session_state:
        try:
            with open(_cache_path) as _f:
                st.session_state["slack_users"] = _json.load(_f)
        except Exception:
            st.session_state["slack_users"] = []
    slack_users: list = st.session_state["slack_users"]

    # ── Add contributor ─────────────────────────────────────────
    sub_header("Add Contributor")
    existing_names = {c["name"].lower() for c in db.get_contributors(cycle)}

    if slack_users:
        options = [""] + [
            u["real_name"] for u in slack_users
            if u["real_name"].lower() not in existing_names
        ]
        ac1, ac2 = st.columns([4, 1])
        selected = ac1.selectbox(
            "Search", options,
            format_func=lambda n: "Type to search…" if n == "" else n,
            label_visibility="collapsed",
        )
        if ac2.button("Add", type="primary", use_container_width=True, disabled=not selected):
            user = next((u for u in slack_users if u["real_name"] == selected), None)
            db.add_contributor(
                cycle, selected,
                email=user.get("email", "") if user else "",
                slack_id=user.get("id", "") if user else "",
            )
            db.log(cycle, f"Contributor added: {selected}", "👤")
            st.toast(f"Added {selected}", icon="👤")
            st.rerun()
        st.caption("Not in the list? Type a name below:")

    # Plain text fallback (also works as override)
    with st.form("add_contrib_manual"):
        m1, m2 = st.columns([4, 1])
        manual_name = m1.text_input("Name", placeholder="Full name", label_visibility="collapsed")
        if m2.form_submit_button("Add", use_container_width=True) and manual_name.strip():
            db.add_contributor(cycle, manual_name.strip())
            db.log(cycle, f"Contributor added: {manual_name.strip()}", "👤")
            st.toast(f"Added {manual_name.strip()}", icon="👤")
            st.rerun()

    # ── Contributor list ────────────────────────────────────────
    contribs = db.get_contributors(cycle)
    if contribs:
        st.divider()
        st.markdown(f"**{len(contribs)}** contributor{'s' if len(contribs) != 1 else ''}")
        st.write("")
        for c in contribs:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{c['name']}**" + (f"  <span style='color:{TEXT_2};font-size:.82rem;'>@{c.get('email','').split('@')[0]}</span>" if c.get('email') else ""), unsafe_allow_html=True)
            if c2.button("✕", key=f"del_{c['id']}", help=f"Remove {c['name']}"):
                db.delete_contributor(c["id"])
                db.log(cycle, f"Contributor removed: {c['name']}", "🗑️")
                st.rerun()
    else:
        st.caption("No contributors added yet.")

    st.write("")
    st.divider()
    _, col_next = st.columns([4, 1])
    if col_next.button("Next: Communications →", use_container_width=True, type="primary"):
        st.session_state["_nav_goto"] = 2
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# SECTION 4 — COMMUNICATIONS
# ═══════════════════════════════════════════════════════════════

def _message_card(title: str, description: str, default_text: str, key_prefix: str, cycle: str):
    """Render a single message card with editable text area and download button."""
    st.markdown(
        f'<div class="msg-card"><h4>{title}</h4>'
        f'<div class="desc">{description}</div></div>',
        unsafe_allow_html=True,
    )

    session_key = f"msg_{key_prefix}_{cycle}"
    if session_key not in st.session_state:
        st.session_state[session_key] = default_text

    msg = st.text_area(
        "Edit before copying",
        key=session_key,
        height=200,
        label_visibility="collapsed",
    )

    bc1, bc2, bc3 = st.columns([1, 1, 3])
    bc1.download_button(
        "📥 Download TXT",
        msg,
        file_name=f"{key_prefix}_{cycle}.txt",
        mime="text/plain",
        key=f"dl_{key_prefix}_{cycle}",
    )
    if bc2.button("🔄 Regenerate", key=f"regen_{key_prefix}_{cycle}"):
        del st.session_state[session_key]
        st.rerun()

    return msg


def render_communications(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("💬 Communications")
    st.write("")

    msgs = _build_messages(ev)
    # Keep session state initialised so the bot-token path can still use it
    session_key = f"msg_contributor_{cycle}"
    if session_key not in st.session_state:
        st.session_state[session_key] = msgs["contributor"]

    slack_ready = slack_ops.is_token_configured()
    channel_name, _ = _channel_and_pres_names(cycle, ev)
    existing_ch_id   = ev.get("slack_channel_id", "")
    existing_ch_name = ev.get("slack_channel_name", "")
    contribs         = db.get_contributors(cycle)
    contrib_with_slack = [c for c in contribs if c.get("slack_id")]

    # Build @mention string for all contributors with a Slack ID
    mentions = " ".join(f"<@{c['slack_id']}>" for c in contribs if c.get("slack_id"))

    # Build message with @mentions replacing "Hi all,"
    base_msg = msgs["contributor"]
    if mentions and base_msg.startswith("Hi all,"):
        msg_with_mentions = f"Hi {mentions},\n" + base_msg[len("Hi all,"):]
    else:
        msg_with_mentions = base_msg

    # Check if already done (share_onboarding checklist item = done)
    already_done = any(
        item.get("id") == "share_onboarding" and item.get("status") == "done"
        for item in ev.get("prep_checklist", [])
    )

    if already_done:
        st.markdown(
            f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
            f'✅ Done — channel created, contributors invited, message posted.</div>',
            unsafe_allow_html=True,
        )
    elif slack_ready:
        confirm_key = f"confirm_contributor_{cycle}"
        confirmed = st.checkbox(
            "✅  This message is ready — create the channel, invite contributors & post",
            key=confirm_key,
        )

        if confirmed:
            final_msg = st.session_state.get(session_key, msgs["contributor"])
            steps, errors = [], []

            with st.spinner("Working…"):
                # Step 1 — create channel
                ch_id = existing_ch_id
                if not ch_id:
                    res = slack_ops.create_channel(channel_name, is_private=True)
                    if res.get("ok"):
                        ch_id = res["channel_id"]
                        db.upsert_event(cycle, slack_channel_id=ch_id, slack_channel_name=res["channel_name"])
                        db.log(cycle, f"Slack channel created: #{res['channel_name']}", "💬")
                        steps.append(f"✅ Channel **#{res['channel_name']}** created")
                    else:
                        errors.append(f"Channel creation failed: {res.get('error')}")
                else:
                    steps.append(f"✅ Channel **#{existing_ch_name}** already exists")

                # Step 2 — invite contributors
                if ch_id and contrib_with_slack:
                    user_ids = [c["slack_id"] for c in contrib_with_slack]
                    inv = slack_ops.invite_users(ch_id, user_ids)
                    if inv.get("ok"):
                        db.log(cycle, "Contributors invited to channel", "👥")
                        steps.append(f"✅ {len(contrib_with_slack)} contributor(s) invited")
                    else:
                        errors.append(f"Invite failed: {inv.get('error')}")
                elif not contrib_with_slack:
                    steps.append("⚠️ No contributors with a Slack ID — skipped invite")

                # Step 3 — post message
                if ch_id and not errors:
                    post = slack_ops.post_message(ch_id, final_msg)
                    if post.get("ok"):
                        db.log(cycle, "Contributor message posted to channel", "💬")
                        steps.append("✅ Message posted")
                        ev2 = db.get_event(cycle)
                        if ev2:
                            updated_prep = [
                                {**item, "status": "done"}
                                if item["id"] in ("create_slack_channel", "share_onboarding")
                                else item
                                for item in ev2.get("prep_checklist", [])
                            ]
                            db.upsert_event(cycle, prep_checklist=updated_prep)
                    else:
                        errors.append(f"Post failed: {post.get('error')}")

            for s in steps:
                st.markdown(s)
            for e in errors:
                st.error(e)

            if not errors:
                st.toast("Done! Channel created, contributors invited, message posted.", icon="🚀")
                st.rerun()

    else:
        # ── Claude-powered path (no bot token yet) ────────────────
        edit_key      = f"msg_contributor_edit_{cycle}"
        reset_key     = f"reset_contributor_edit_{cycle}"
        edit_override = f"comm_edit_override_{cycle}"

        msg_status  = ev.get("contributor_msg_status", "")
        is_approved = msg_status == "approved"

        if is_approved and not st.session_state.get(edit_override, False):
            # ── Approved / read-only view ─────────────────────────
            ch_saved = ev.get("slack_channel_name", "").strip().lstrip("#")
            st.markdown(
                f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;'
                f'padding:16px;margin-bottom:10px;">'
                f'<div style="font-size:.75rem;color:{TEXT_2};margin-bottom:8px;">#{ch_saved}</div>'
                f'<pre style="color:{TEXT_1};font-size:.85rem;white-space:pre-wrap;margin:0;">'
                f'{ev.get("contributor_msg_final", "")}</pre></div>',
                unsafe_allow_html=True,
            )
            ec1, _ = st.columns([1, 3])
            if ec1.button("✏️ Edit message", key=f"comm_edit_btn_{cycle}", use_container_width=True):
                st.session_state[edit_override] = True
                db.upsert_event(cycle, contributor_msg_status="draft")
                st.rerun()

            st.markdown(
                f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
                f'✅ <strong>Approved</strong> — check your Slack <strong>Drafts & Sent</strong> for <strong>#{ch_saved}</strong> '
                f'to review and send. Edit directly in Slack if anything needs tweaking.</div>',
                unsafe_allow_html=True,
            )

        else:
            # ── Edit view ─────────────────────────────────────────
            st.markdown(
                f'<div class="msg-card"><h4>Contributor Channel Message</h4>'
                f'<div class="desc">Edit freely below. The <code>&lt;@U…&gt;</code> codes are Slack @mentions — '
                f'they render as real names in Slack. '
                f'Slack will prompt you to invite anyone not yet in the channel.</div></div>',
                unsafe_allow_html=True,
            )

            if st.session_state.pop(reset_key, False):
                st.session_state[edit_key] = msg_with_mentions
            elif edit_key not in st.session_state:
                saved_draft = ev.get("contributor_msg_final", "")
                st.session_state[edit_key] = saved_draft if saved_draft else msg_with_mentions

            st.text_area(
                "Edit message",
                key=edit_key,
                height=260,
                label_visibility="collapsed",
            )
            regen_col, _ = st.columns([1, 5])
            if regen_col.button("🔄 Reset to default", key=f"regen_edit_{cycle}"):
                st.session_state[reset_key] = True
                st.rerun()

            st.write("")

            saved_ch = ev.get("slack_channel_name", "")
            ch_col, _ = st.columns([3, 1])
            ch_input = ch_col.text_input(
                "Channel name (no #) — create it in Slack first if needed",
                value=saved_ch,
                placeholder=channel_name,
                key=f"ch_name_input_{cycle}",
            )

            st.write("")

            btn_disabled = not ch_input.strip()
            _, approve_col, _ = st.columns([1, 2, 2])

            if approve_col.button("✅ Save & Approve", key=f"approve_draft_{cycle}",
                                  type="primary", disabled=btn_disabled, use_container_width=True):
                ch   = ch_input.strip().lstrip("#") or channel_name
                text = st.session_state.get(edit_key, msg_with_mentions)
                db.upsert_event(cycle, slack_channel_name=ch,
                                contributor_msg_final=text, contributor_msg_status="approved")
                db.log(cycle, f"Contributor message approved for #{ch}", "💬")
                slack_ops.save_as_slack_draft_background(ch, text)
                st.session_state.pop(edit_override, None)
                st.rerun()

    # ── Next ─────────────────────────────────────────────────────
    st.write("")
    st.divider()
    _, col_next = st.columns([4, 1])
    if col_next.button("Next: New Joiners →", use_container_width=True, type="primary"):
        st.session_state["_nav_goto"] = 3
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# SECTION 5 — DAY-OF & POST-EVENT OPERATIONS
# ═══════════════════════════════════════════════════════════════

def render_operations(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return
    ev = _ensure_checklists(cycle, ev)

    section_header("🎬 Day-of & Post-Event Operations")

    ops = ev.get("ops_checklist", [])
    day_of = [i for i in ops if i.get("phase") == "day_of"]
    post_ev = [i for i in ops if i.get("phase") == "post_event"]

    done_count = sum(1 for i in ops if i.get("status") == "done")
    st.markdown(
        f"**{done_count}/{len(ops)}** tasks completed  "
        + _status_badge("done" if done_count == len(ops) else "in_progress"),
        unsafe_allow_html=True,
    )
    st.write("")

    with st.form("ops_form"):
        sub_header("Day-of Checklist")
        for i, item in enumerate(day_of):
            c1, c2, c3 = st.columns([1.5, 4, 2.5])
            current = STATUS_REVERSE.get(item.get("status", "not_started"), "Not started")
            c1.selectbox(
                f"ds_{i}",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current),
                key=f"ops_ds_{i}",
                label_visibility="collapsed",
            )
            c2.text_input(f"dt_{i}", value=item["task"], disabled=True, key=f"ops_dt_{i}", label_visibility="collapsed")
            c3.text_input(
                f"dn_{i}",
                value=item.get("notes", ""),
                placeholder="Notes",
                key=f"ops_dn_{i}",
                label_visibility="collapsed",
            )

        sub_header("Post-Event Checklist")
        for j, item in enumerate(post_ev):
            c1, c2, c3 = st.columns([1.5, 4, 2.5])
            current = STATUS_REVERSE.get(item.get("status", "not_started"), "Not started")
            c1.selectbox(
                f"ps_{j}",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current),
                key=f"ops_ps_{j}",
                label_visibility="collapsed",
            )
            c2.text_input(f"pt_{j}", value=item["task"], disabled=True, key=f"ops_pt_{j}", label_visibility="collapsed")
            c3.text_input(
                f"pn_{j}",
                value=item.get("notes", ""),
                placeholder="Notes",
                key=f"ops_pn_{j}",
                label_visibility="collapsed",
            )

        save_ops = st.form_submit_button("Save Operations Checklist", type="primary", use_container_width=True)

    if save_ops:
        updated = []
        di, pi = 0, 0
        for item in ops:
            if item.get("phase") == "day_of":
                item["status"] = STATUS_MAP.get(st.session_state[f"ops_ds_{di}"], "not_started")
                item["notes"] = st.session_state[f"ops_dn_{di}"]
                di += 1
            else:
                item["status"] = STATUS_MAP.get(st.session_state[f"ops_ps_{pi}"], "not_started")
                item["notes"] = st.session_state[f"ops_pn_{pi}"]
                pi += 1
            updated.append(item)
        db.upsert_event(cycle, ops_checklist=updated)
        db.log(cycle, "Operations checklist updated", "✅")
        st.toast("Operations checklist saved!", icon="✅")
        st.rerun()

    st.divider()
    sub_header("Post-Event Links")
    st.caption("Fill in after the event. These feed into the follow-up message in Communications.")
    with st.form("post_event_links_form"):
        pe1, pe2 = st.columns(2)
        recording_link = pe1.text_input("Recording link", value=ev.get("recording_link", ""))
        recording_passcode = pe2.text_input("Recording passcode", value=ev.get("recording_passcode", ""))
        feedback_survey_link = st.text_input("Feedback survey link", value=ev.get("feedback_survey_link", ""))
        save_links = st.form_submit_button("Save Post-Event Links", type="primary", use_container_width=True)

    if save_links:
        db.upsert_event(
            cycle,
            recording_link=recording_link,
            recording_passcode=recording_passcode,
            feedback_survey_link=feedback_survey_link,
        )
        db.log(cycle, "Post-event links saved", "✅")
        st.toast("Post-event links saved!", icon="✅")
        st.rerun()

    # ── Feedback survey creation ────────────────────────────────
    st.divider()
    sub_header("📊 Feedback Survey")

    existing_survey = ev.get("feedback_survey_link", "")
    if existing_survey:
        st.markdown(
            f'<div class="smart-alert">✅ Survey already created: '
            f'<a href="{existing_survey}" target="_blank" style="color:inherit;">'
            f'open form ↗</a></div>',
            unsafe_allow_html=True,
        )
    else:
        ev_date_str = ev.get("event_date", "")
        survey_ready = bool(ev_date_str)
        if not survey_ready:
            st.caption("⚠️ Set an event date first.")
        if st.button(
            "📊 Create Google Form Survey",
            disabled=not survey_ready,
            use_container_width=False,
        ):
            result = drive.create_survey(ev_date_str, location="Remote - EMEA")
            if result.get("ok"):
                db.upsert_event(cycle, feedback_survey_link=result["url"])
                # auto-mark create_feedback + store_form checklist items as done
                ev2 = db.get_event(cycle)
                if ev2:
                    updated = [
                        {**item, "status": "done"}
                        if item["id"] in ("create_feedback", "store_form")
                        else item
                        for item in ev2.get("ops_checklist", [])
                    ]
                    db.upsert_event(cycle, ops_checklist=updated)
                db.log(cycle, "Feedback survey created", "📊")
                st.toast("Feedback survey created!", icon="📊")
                st.rerun()
            else:
                st.error(f"Drive error: {result.get('error')}")


# ═══════════════════════════════════════════════════════════════
# SECTION 5 — AUTO REMINDERS
# ═══════════════════════════════════════════════════════════════

def render_auto_reminders(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("⏰ Auto Reminders")
    st.caption(
        "Configure the messages you want sent on a specific date and time. "
        "Approve each one — when the app is opened and a reminder is due, you'll see an alert and can send with one click."
    )
    st.write("")

    slack_ready = slack_ops.is_token_configured()
    msgs = _build_messages(ev)
    reminders = ev.get("reminders", [])
    contrib_ch = ev.get("slack_channel_name", "").lstrip("#") or "contributor-channel"

    # Ensure contributor_pre_event exists as the first reminder
    ids = {r["id"] for r in reminders}
    if "contributor_pre_event" not in ids:
        reminders.insert(0, {
            "id": "contributor_pre_event",
            "name": "Pre-Event Reminder (Contributors)",
            "description": f"Sent to the private contributor channel #{contrib_ch} before the event",
            "message": templates.contributor_pre_event_reminder(),
            "channel": contrib_ch,
            "scheduled_date": ev.get("event_date", ""),
            "scheduled_time": "09:00",
            "status": "pending",
            "sent_ts": "",
        })
        db.upsert_event(cycle, reminders=reminders)

    # Ensure pre_event (event day) exists
    if "pre_event" not in ids:
        reminders.append({
            "id": "pre_event",
            "name": "Event Day Reminder",
            "description": "Post in #online-monthly-emea-all-hands on the morning of the event",
            "message": msgs["pre_event"],
            "channel": "online-monthly-emea-all-hands",
            "scheduled_date": ev.get("event_date", ""),
            "scheduled_time": "09:00",
            "status": "pending",
            "sent_ts": "",
        })
        db.upsert_event(cycle, reminders=reminders)

    # Only show contributor_pre_event and pre_event here — post_event lives on Post Event page
    display_reminders = [r for r in reminders if r["id"] in ("contributor_pre_event", "pre_event")]
    updated_reminders = list(reminders)

    for i, r in enumerate(display_reminders):
        status = r.get("status", "pending")

        # Check if due
        is_due = False
        if status == "approved" and r.get("scheduled_date") and r.get("scheduled_time"):
            try:
                sched_dt = datetime.strptime(
                    f"{r['scheduled_date']} {r['scheduled_time']}", "%Y-%m-%d %H:%M"
                )
                is_due = sched_dt <= datetime.now()
            except Exception:
                pass

        badge_map = {
            "pending":  ("default", "Draft"),
            "approved": ("warn",    "⏳ Approved"),
            "sent":     ("ok",      "✅ Sent"),
        }
        bv, bl = badge_map.get(status, ("default", status.title()))
        if is_due:
            bv, bl = "err", "🔔 Due Now"

        st.markdown(
            f'<div class="msg-card">'
            f'<h4>{r["name"]}  <span class="b b-{bv}">{bl}</span></h4>'
            f'<div class="desc">{r.get("description", "")}</div></div>',
            unsafe_allow_html=True,
        )

        if status == "sent":
            st.markdown(
                f'<div class="smart-alert">✅ Sent on {r.get("sent_ts", "—")}</div>',
                unsafe_allow_html=True,
            )
            st.write("")
            continue

        msg_key   = f"rem_msg_{r['id']}_{cycle}"
        edit_flag = f"rem_editing_{r['id']}_{cycle}"

        sched_date_default = date.today()
        if r.get("scheduled_date"):
            try:
                sched_date_default = datetime.strptime(r["scheduled_date"], "%Y-%m-%d").date()
            except Exception:
                pass

        is_editing = st.session_state.get(edit_flag, status != "approved")

        if status == "approved" and not is_editing:
            # ── Read / approved view ──────────────────────────────
            sched_date = r.get("scheduled_date", "")
            sched_time = r.get("scheduled_time", "")
            ch = r.get("channel", "")
            st.markdown(
                f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;'
                f'padding:16px;margin-bottom:10px;">'
                f'<div style="font-size:.75rem;color:{TEXT_2};margin-bottom:8px;">'
                f'#{ch} · {sched_date} at {sched_time}</div>'
                f'<pre style="color:{TEXT_1};font-size:.85rem;white-space:pre-wrap;margin:0;">'
                f'{r.get("message","")}</pre></div>',
                unsafe_allow_html=True,
            )
            ec1, _ = st.columns([1, 3])
            if ec1.button("✏️ Edit message", key=f"rem_edit_btn_{r['id']}_{cycle}",
                          use_container_width=True):
                st.session_state[edit_flag] = True
                new_r = {**r, "status": "pending"}
                updated_reminders = [new_r if x["id"] == r["id"] else x for x in updated_reminders]
                db.upsert_event(cycle, reminders=updated_reminders)
                st.rerun()

            st.markdown(
                f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
                f'✅ <strong>Approved</strong> — scheduled in Slack for <strong>#{ch}</strong> '
                f'on {sched_date} at {sched_time}. '
                f'Edit directly in Slack Drafts &amp; Sent if anything needs tweaking.</div>',
                unsafe_allow_html=True,
            )

        else:
            # ── Edit view ─────────────────────────────────────────
            if msg_key not in st.session_state:
                st.session_state[msg_key] = r.get("message", "")

            with st.form(f"rem_form_{r['id']}_{cycle}"):
                fc1, fc2, fc3 = st.columns([2, 1, 1])
                fc1.text_input(
                    "Post to channel (without #)",
                    value=r.get("channel", ""),
                    key=f"rem_ch_{i}_{cycle}",
                )
                fc2.date_input(
                    "Date", value=sched_date_default,
                    key=f"rem_d_{i}_{cycle}", format="DD/MM/YYYY",
                )
                fc3.text_input(
                    "Time (HH:MM)", value=r.get("scheduled_time", "09:00"),
                    key=f"rem_t_{i}_{cycle}",
                )
                st.text_area("Message", key=msg_key, height=180, label_visibility="collapsed")

                _, btn1, _ = st.columns(3)
                approve_btn = btn1.form_submit_button(
                    "✅ Save & Approve", type="primary", use_container_width=True,
                )

            if approve_btn:
                sched_date_val = st.session_state.get(f"rem_d_{i}_{cycle}", sched_date_default)
                new_r = {
                    **r,
                    "channel":        st.session_state.get(f"rem_ch_{i}_{cycle}", r.get("channel", "")),
                    "scheduled_date": str(sched_date_val),
                    "scheduled_time": st.session_state.get(f"rem_t_{i}_{cycle}", r.get("scheduled_time", "")),
                    "message":        st.session_state.get(msg_key, r.get("message", "")),
                    "status":         "approved",
                }
                st.session_state[edit_flag] = False
                db.log(cycle, f"Reminder approved: {r['name']}", "✅")
                slack_ops.schedule_reminder_background(
                    new_r["channel"], new_r["message"],
                    new_r["scheduled_date"], new_r["scheduled_time"],
                )
                st.toast(f"'{r['name']}' approved!", icon="✅")
                updated_reminders = [new_r if x["id"] == r["id"] else x for x in updated_reminders]
                db.upsert_event(cycle, reminders=updated_reminders)
                st.rerun()

        st.write("")

    # ── Next ─────────────────────────────────────────────────────
    st.write("")
    st.divider()
    _, col_next = st.columns([4, 1])
    if col_next.button("Next: Post Event →", use_container_width=True, type="primary"):
        st.session_state["_nav_goto"] = 5
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# SECTION 6 — POST EVENT COMMUNICATIONS
# ═══════════════════════════════════════════════════════════════

def render_post_event(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("📮 Post Event Communications")
    st.caption(
        "Fill in the recording and survey links after the event, "
        "then approve the follow-up message and ask Claude to post it."
    )
    st.write("")

    slack_ready = slack_ops.is_token_configured()

    # ── Post-event links ─────────────────────────────────────────
    sub_header("Event Links")
    st.caption("Fill these in after the event — they'll be auto-inserted into the message below.")

    with st.form("post_event_links_form"):
        pe1, pe2 = st.columns(2)
        recording_link     = pe1.text_input("Recording link",     value=ev.get("recording_link", ""))
        recording_passcode = pe2.text_input("Recording passcode", value=ev.get("recording_passcode", ""))
        feedback_survey    = st.text_input("Feedback survey link", value=ev.get("feedback_survey_link", ""))
        save_links = st.form_submit_button("💾 Save links", type="primary", use_container_width=True)

    if save_links:
        db.upsert_event(
            cycle,
            recording_link=recording_link,
            recording_passcode=recording_passcode,
            feedback_survey_link=feedback_survey,
        )
        db.log(cycle, "Post-event links saved", "🔗")
        # Drop the cached message so it regenerates with the new links
        st.session_state.pop(f"post_event_msg_{cycle}", None)
        st.toast("Links saved — follow-up message updated!", icon="🔗")
        st.rerun()

    # ── Feedback Survey ──────────────────────────────────────────
    st.write("")
    sub_header("Feedback Survey")

    existing_survey = ev.get("feedback_survey_link", "")
    if existing_survey:
        st.markdown(
            f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
            f'✅ Survey ready: <a href="{existing_survey}" target="_blank" '
            f'style="color:{SUCCESS};">open form ↗</a></div>',
            unsafe_allow_html=True,
        )
    else:
        ev_date_str = ev.get("event_date", "")
        folder_link = ev.get("emea_folder_link", "")
        survey_ready = bool(ev_date_str)
        if not survey_ready:
            st.caption("⚠️ Set an event date in Event Setup first.")
        if st.button("📊 Create Feedback Survey", disabled=not survey_ready, use_container_width=False):
            folder_id = drive.extract_file_id(folder_link) if folder_link else None
            result = drive.create_survey(ev_date_str, location="Remote - EMEA", folder_id=folder_id)
            if result.get("ok"):
                db.upsert_event(cycle, feedback_survey_link=result["url"])
                db.log(cycle, "Feedback survey created and saved to Drive folder", "📊")
                st.toast("Survey created and saved to your Drive folder!", icon="📊")
                st.rerun()
            else:
                st.error(f"Could not create survey: {result.get('error')}")

    # ── Message ──────────────────────────────────────────────────
    st.write("")
    sub_header("Follow-Up Message")
    st.caption("Edit freely — links are auto-filled from the fields above.")

    rec  = ev.get("recording_link", "") or "[recording link]"
    pas  = ev.get("recording_passcode", "") or "[passcode]"
    surv = ev.get("feedback_survey_link", "") or "[survey link]"
    default_post_msg = templates.post_event_followup(rec, pas, surv)

    pe_msg_key   = f"post_event_msg_{cycle}"
    pe_reset_key = f"post_event_msg_reset_{cycle}"

    if st.session_state.pop(pe_reset_key, False):
        st.session_state[pe_msg_key] = default_post_msg
    elif pe_msg_key not in st.session_state:
        st.session_state[pe_msg_key] = ev.get("post_event_msg_final") or default_post_msg

    st.text_area("Follow-up message", key=pe_msg_key, height=260, label_visibility="collapsed")

    rc1, _ = st.columns([1, 5])
    if rc1.button("🔄 Reset to default", key=f"regen_post_event_{cycle}"):
        st.session_state[pe_reset_key] = True
        st.rerun()

    # ── Approve ──────────────────────────────────────────────────
    st.write("")
    sub_header("Approve")

    already_sent = ev.get("post_event_status") == "sent"

    if already_sent:
        st.markdown(
            f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
            f'✅ Post-event follow-up sent.</div>',
            unsafe_allow_html=True,
        )
    else:
        with st.form("post_event_schedule_form"):
            sc1, sc2, sc3 = st.columns([2, 1, 1])
            pe_channel = sc1.text_input(
                "Post to channel (no #)",
                value=ev.get("post_event_channel", "online-monthly-emea-all-hands"),
            )
            pe_date_default = date.today()
            if ev.get("post_event_scheduled_date"):
                try:
                    pe_date_default = datetime.strptime(ev["post_event_scheduled_date"], "%Y-%m-%d").date()
                except Exception:
                    pass
            pe_date = sc2.date_input("Date", value=pe_date_default, format="DD/MM/YYYY")
            pe_time = sc3.text_input("Time (HH:MM)", value=ev.get("post_event_scheduled_time", "17:00"))

            approved = ev.get("post_event_status") == "approved"
            fb1, _, fb2 = st.columns(3)
            approve_btn = fb1.form_submit_button(
                "✅ Approve", type="primary", use_container_width=True,
                disabled=approved,
            )
            save_btn = fb2.form_submit_button("💾 Save", use_container_width=True)

        if approve_btn or save_btn:
            final_msg = st.session_state.get(pe_msg_key, default_post_msg)
            updates = {
                "post_event_channel":        pe_channel,
                "post_event_scheduled_date": str(pe_date),
                "post_event_scheduled_time": pe_time,
                "post_event_msg_final":      final_msg,
            }
            if approve_btn:
                updates["post_event_status"] = "approved"
                db.log(cycle, "Post-event follow-up approved", "✅")
                st.toast("Approved! Tell Claude to save as Slack draft.", icon="✅")
            else:
                st.toast("Saved!", icon="💾")

            db.upsert_event(cycle, **updates)
            st.rerun()

        if ev.get("post_event_status") == "approved":
            ch = ev.get("post_event_channel", "online-monthly-emea-all-hands")
            st.markdown(
                f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
                f'✅ <strong>Approved!</strong> Tell Claude:<br>'
                f'<em>"Save the post-event follow-up for the {cycle} EMEA All Hands as a draft in #{ch}"</em><br>'
                f'<span style="font-size:.8rem;opacity:.7;">'
                f'Claude saves it to your Slack Drafts — you review and hit Send.</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")
    st.divider()
    _, col_next = st.columns([4, 1])
    if col_next.button("Next: Notion Folder →", use_container_width=True, type="primary"):
        st.session_state["_nav_goto"] = 6
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# SECTION 7 — EXPORTS
# ═══════════════════════════════════════════════════════════════

def render_exports(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("📤 Outputs & Exports")
    st.caption(
        "Download the full event plan in multiple formats. "
        "Exports include event details, checklists, contributor summary, and communications."
    )
    st.write("")

    contribs = db.get_contributors(cycle)
    msgs = _build_messages(ev)
    for key in ["contributor", "pre_event", "post_event"]:
        sk = f"msg_{key}_{cycle}"
        if sk in st.session_state:
            msgs[key] = st.session_state[sk]

    plain = exports.generate_plain_text(ev, contribs, msgs)
    html = exports.generate_html(ev, contribs, msgs)
    pdf_bytes = exports.generate_pdf_bytes(ev, contribs, msgs)

    st.markdown('<div class="card"><h4>Available Formats</h4></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.download_button(
        "📄 Plain Text",
        plain,
        file_name=f"EMEA_AllHands_{cycle}.txt",
        mime="text/plain",
        use_container_width=True,
    )
    c2.download_button(
        "🌐 HTML Summary",
        html,
        file_name=f"EMEA_AllHands_{cycle}.html",
        mime="text/html",
        use_container_width=True,
    )
    if pdf_bytes:
        c3.download_button(
            "📕 PDF Summary",
            pdf_bytes,
            file_name=f"EMEA_AllHands_{cycle}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        c3.button("📕 PDF (install fpdf2)", disabled=True, use_container_width=True)

    c4.download_button(
        "📋 Google Doc (TXT)",
        plain,
        file_name=f"EMEA_AllHands_{cycle}_gdoc.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.divider()
    sub_header("Preview — Plain Text")
    with st.expander("Show preview", expanded=False):
        st.code(plain, language=None)

    sub_header("Preview — HTML")
    with st.expander("Show preview", expanded=False):
        st.components.v1.html(html, height=800, scrolling=True)


# ═══════════════════════════════════════════════════════════════
# SECTION 7 — NOTION FOLDER
# ═══════════════════════════════════════════════════════════════

def render_notion_folder(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("📒 Notion Folder")
    st.caption("All EMEA All Hands presentations are stored here for easy reference.")
    st.write("")

    # ── Notion page link ─────────────────────────────────────────
    st.markdown(
        f'<div class="card">'
        f'<h4>📒 EMEA All Hands — Notion Page</h4>'
        f'<p>The Notion page contains all previous EMEA All Hands presentations '
        f'in one place — organised by date, most recent first.</p>'
        f'<a href="{NOTION_PAGE_URL}" target="_blank" '
        f'style="display:inline-block;margin-top:8px;padding:8px 20px;'
        f'background:{INDIGO};color:#fff;border-radius:8px;'
        f'font-weight:600;font-size:.88rem;text-decoration:none;">'
        f'Open Notion Folder ↗</a>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Save presentation to Notion ───────────────────────────────
    pres_url   = ev.get("presentation_link", "")
    pres_title = ev.get("presentation_title", "")
    ev_date    = ev.get("event_date", "")
    already_saved = bool(ev.get("notion_saved", False))

    st.write("")
    sub_header("Save Presentation to Notion")

    if already_saved:
        st.markdown(
            f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
            f'✅ <strong>Saved to Notion</strong> — '
            f'<a href="{NOTION_PAGE_URL}" target="_blank" style="color:{SUCCESS};">'
            f'{pres_title or "open Notion page"} ↗</a></div>',
            unsafe_allow_html=True,
        )
    elif pres_url:
        ev_date_fmt = ev_date
        try:
            from datetime import datetime as _dt
            ev_date_fmt = _dt.strptime(ev_date, "%Y-%m-%d").strftime("%-d %b %Y")
        except Exception:
            pass
        pres_title_clean = pres_title.replace("_", " ")

        st.markdown(
            f'<div class="smart-alert">📊 Ready to save: <strong>{pres_title}</strong></div>',
            unsafe_allow_html=True,
        )
        st.caption("Copy the prompt below and run it in Claude Code to add the presentation to Notion:")
        claude_prompt = (
            f'Add this EMEA All Hands presentation to the top of the Presentations table '
            f'on the Notion page https://app.notion.com/p/affirm/EMEA-All-Hands-10d40e54ae38807eb40fd687c7f7a306 — '
            f'Date: {ev_date_fmt}, Title: {pres_title_clean}, '
            f'Link: {pres_url}'
        )
        st.code(claude_prompt, language=None)

        if st.button("✅ Mark as saved to Notion", use_container_width=False):
            db.upsert_event(cycle, notion_saved=True)
            db.log(cycle, f"Presentation saved to Notion: {pres_title}", "📒")
            st.toast("Marked as saved!", icon="📒")
            st.rerun()
    else:
        st.markdown(
            f'<div class="smart-alert" style="color:{WARNING};">'
            f'⚠️ No presentation link yet — go back to Event Setup to create one.</div>',
            unsafe_allow_html=True,
        )

    st.write("")
    st.divider()
    st.markdown(
        f'<div style="color:{TEXT_2};font-size:.85rem;text-align:center;padding:8px 0;">'
        f'🎉 All done! This event is fully set up.</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# SECTION — NEW JOINERS SLIDE
# ═══════════════════════════════════════════════════════════════

def render_new_joiners(cycle: str):
    ev = db.get_event(cycle)
    if not ev:
        st.warning("Create an event first.")
        return

    section_header("🆕 New Joiners Slide")
    st.write("")

    pres_url = ev.get("presentation_link", "")

    # ══ STAGE 1: Date Range ══════════════════════════════════════
    st.markdown(
        f'<div class="sub-hdr">1 · Select Date Range</div>',
        unsafe_allow_html=True,
    )

    start_default = date.today().replace(day=1)
    end_default   = date.today()
    if ev.get("new_joiners_start_date"):
        try:
            start_default = datetime.strptime(ev["new_joiners_start_date"], "%Y-%m-%d").date()
        except ValueError:
            pass
    if ev.get("new_joiners_end_date"):
        try:
            end_default = datetime.strptime(ev["new_joiners_end_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    dates_approved = bool(ev.get("new_joiners_start_date") and ev.get("new_joiners_end_date"))

    with st.form(f"nj_dates_{cycle}"):
        d1, d2, d3 = st.columns([2, 2, 2])
        start_date  = d1.date_input("Start date", value=start_default, format="DD/MM/YYYY")
        end_date    = d2.date_input("End date",   value=end_default,   format="DD/MM/YYYY")
        approve_btn = d3.form_submit_button("✅ Approve Dates", type="primary", use_container_width=True)

    if approve_btn:
        _clear_nj_session_state(cycle)
        db.upsert_event(cycle,
            new_joiners_start_date=str(start_date),
            new_joiners_end_date=str(end_date),
            new_joiners_data=[],
            new_joiners_slide_updated=False,
            new_joiners_fetching=True,
        )
        db.log(cycle, f"New joiners dates approved: {start_date} → {end_date}", "🆕")
        st.toast("Dates approved! Claude will now fetch from Workday.", icon="✅")
        st.rerun()

    nj_start = ev.get("new_joiners_start_date") or str(start_default)
    nj_end   = ev.get("new_joiners_end_date")   or str(end_default)
    try:
        start_fmt = datetime.strptime(nj_start, "%Y-%m-%d").strftime("%-d %b %Y")
        end_fmt   = datetime.strptime(nj_end,   "%Y-%m-%d").strftime("%-d %b %Y")
    except Exception:
        start_fmt, end_fmt = nj_start, nj_end
    period_label = f"{start_fmt} – {end_fmt}"

    if dates_approved:
        st.markdown(
            f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
            f'✅ <strong>{period_label}</strong> — tell Claude to go fetch from Workday.</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # ══ STAGE 2: People List ══════════════════════════════════════
    st.markdown(
        f'<div class="sub-hdr">2 · New Joiners List</div>',
        unsafe_allow_html=True,
    )

    people = ev.get("new_joiners_data", [])

    fetching = bool(ev.get("new_joiners_fetching", False))

    if not people:
        if fetching:
            st.markdown(
                f'<div class="card" style="text-align:center;padding:32px 24px;'
                f'border-color:{INDIGO}44;">'
                f'<p style="font-size:1.5rem;margin:0 0 8px;">⏳</p>'
                f'<p style="color:{TEXT_1};font-weight:600;margin:0 0 6px;">'
                f'Gathering data from Workday…</p>'
                f'<p style="color:{TEXT_2};font-size:.85rem;margin:0 0 16px;">'
                f'Claude is fetching the new joiners list and photos for {period_label}.<br>'
                f'This usually takes a few minutes. The list will appear here as soon as it\'s ready.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("🔄 Refresh", key=f"nj_refresh_{cycle}", use_container_width=False):
                st.rerun()
        else:
            st.markdown(
                f'<div class="card" style="text-align:center;padding:32px 24px;">'
                f'<p style="font-size:1.5rem;margin:0 0 8px;">👥</p>'
                f'<p style="color:{TEXT_2};margin:0;">'
                f'{"Approve the dates above — Claude will fetch from Workday automatically." if not dates_approved else "No data yet. Tell Claude to fetch from Workday."}'
                f'</p></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f'<div style="color:{TEXT_2};font-size:.82rem;margin-bottom:12px;">'
            f'{len(people)} person{"s" if len(people) != 1 else ""} · {period_label} · '
            f'Edit any field, ✕ to remove</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="display:grid;grid-template-columns:0.7fr 2fr 2.5fr 2fr 0.6fr;'
            f'gap:8px;padding:4px 0 6px;font-size:.75rem;font-weight:600;color:{TEXT_2};">'
            f'<div>Flag</div><div>Name</div><div>Title</div><div>Location</div><div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        to_delete = None
        for i, p in enumerate(people):
            for field, default in [("flag", "🌍"), ("name", ""), ("title", ""), ("location", "")]:
                k = f"nj_{field}_{i}_{cycle}"
                if k not in st.session_state:
                    st.session_state[k] = p.get(field, default)
            c1, c2, c3, c4, c5 = st.columns([0.7, 2, 2.5, 2, 0.6])
            c1.text_input("Flag",     key=f"nj_flag_{i}_{cycle}",  label_visibility="collapsed")
            c2.text_input("Name",     key=f"nj_name_{i}_{cycle}",  label_visibility="collapsed")
            c3.text_input("Title",    key=f"nj_title_{i}_{cycle}", label_visibility="collapsed")
            c4.text_input("Location", key=f"nj_loc_{i}_{cycle}",   label_visibility="collapsed")
            if c5.button("✕", key=f"nj_del_{i}_{cycle}", help=f"Remove {p.get('name', '')}"):
                to_delete = i

        if to_delete is not None:
            people.pop(to_delete)
            _clear_nj_session_state(cycle)
            db.upsert_event(cycle, new_joiners_data=people)
            db.log(cycle, "New joiner removed", "🗑️")
            st.rerun()

        sv1, _ = st.columns([1, 4])
        if sv1.button("💾 Save Changes", key=f"nj_save_{cycle}", type="primary"):
            updated = [
                {
                    "flag":     st.session_state.get(f"nj_flag_{i}_{cycle}", ""),
                    "name":     st.session_state.get(f"nj_name_{i}_{cycle}", ""),
                    "title":    st.session_state.get(f"nj_title_{i}_{cycle}", ""),
                    "location": st.session_state.get(f"nj_loc_{i}_{cycle}", ""),
                }
                for i in range(len(people))
            ]
            db.upsert_event(cycle, new_joiners_data=updated)
            db.log(cycle, "New joiners list updated", "✏️")
            st.toast("Changes saved!", icon="💾")
            st.rerun()

        st.write("")

    with st.form(f"nj_add_{cycle}"):
        st.caption("Add a person manually:")
        a1, a2, a3, a4, a5 = st.columns([0.7, 2, 2.5, 2, 0.6])
        a_flag  = a1.text_input("Flag",     placeholder="🌍",            label_visibility="collapsed")
        a_name  = a2.text_input("Name",     placeholder="Full name",     label_visibility="collapsed")
        a_title = a3.text_input("Title",    placeholder="Job title",     label_visibility="collapsed")
        a_loc   = a4.text_input("Location", placeholder="City, Country", label_visibility="collapsed")
        add_btn = a5.form_submit_button("＋", use_container_width=True)

    if add_btn and a_name.strip():
        people.append({
            "flag":     a_flag.strip() or _get_flag(a_loc.strip()),
            "name":     a_name.strip(),
            "title":    a_title.strip(),
            "location": a_loc.strip(),
        })
        _clear_nj_session_state(cycle)
        db.upsert_event(cycle, new_joiners_data=people)
        db.log(cycle, f"New joiner added manually: {a_name.strip()}", "➕")
        st.toast(f"Added {a_name.strip()}!", icon="➕")
        st.rerun()

    st.write("")

    # ══ STAGE 3: Update Slide ═════════════════════════════════════
    st.markdown(
        f'<div class="sub-hdr">3 · Update Presentation Slide</div>',
        unsafe_allow_html=True,
    )

    slide_done = bool(ev.get("new_joiners_slide_updated", False))

    if slide_done:
        st.markdown(
            f'<div class="smart-alert" style="background:#10b98122;border-color:#10b98144;color:{SUCCESS};">'
            f'✅ Slide already updated for this event. Click below to re-run if you made changes.</div>',
            unsafe_allow_html=True,
        )

    if not pres_url:
        st.markdown(
            f'<div class="smart-alert" style="color:{WARNING};">'
            f'⚠️ No presentation yet — create one in Event Setup first.</div>',
            unsafe_allow_html=True,
        )
    else:
        what = (
            f"<strong>{len(people)} new joiner{'s' if len(people) != 1 else ''}</strong> · "
            f"{period_label} · name, title, location + flag"
            if people else "Set the date range and let Claude fetch from Workday first."
        )
        st.markdown(
            f'<div class="smart-alert">'
            f'Will add to <a href="{pres_url}" target="_blank" style="color:{LIGHT_INDIGO};">'
            f'{ev.get("presentation_title", "your presentation")}</a>: {what}<br>'
            f'<span style="font-size:.8rem;opacity:.7;">'
            f'Looks for a slide titled "New Joiners" or "Welcome" and updates it; '
            f'otherwise inserts a new slide after the cover.</span></div>',
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button(
            "🎨 Update Slide",
            key=f"nj_update_{cycle}",
            type="primary",
            disabled=not people,
        ):
            pres_id = drive.extract_file_id(pres_url)
            with st.spinner("Updating slide…"):
                result = drive.update_new_joiners_slide(pres_id, people, period_label)
            if result.get("ok"):
                action = result.get("action", "updated")
                db.upsert_event(cycle, new_joiners_slide_updated=True)
                db.log(cycle, f"New joiners slide {action} — {len(people)} people", "🎨")
                st.toast(f"Slide {action}!", icon="🎨")
                st.rerun()
            else:
                st.error(f"Slides API error: {result.get('error')}")

    # ── Next ──────────────────────────────────────────────────────
    st.write("")
    st.divider()
    _, col_next = st.columns([4, 1])
    if col_next.button("Next: Auto Reminders →", use_container_width=True, type="primary"):
        st.session_state["_nav_goto"] = 4
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="EMEA All Hands Command Center",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    cycle = st.session_state.get("current_cycle")

    # ── Home page ──────────────────────────────────────────────
    if not cycle:
        with st.sidebar:
            st.markdown(
                f"""<div style="text-align:center;padding:12px 0 8px;">
                    <span style="font-size:1.8rem;font-weight:800;color:{INDIGO};">EMEA</span><br>
                    <span style="font-size:.72rem;color:{TEXT_2};letter-spacing:3px;font-weight:500;">
                        ALL HANDS COMMAND CENTER
                    </span>
                </div>""",
                unsafe_allow_html=True,
            )
            all_active = [
                (c, db.get_event(c)) for c in db.list_cycles()
                if db.get_event(c) and db.get_event(c).get("event_date")
            ]
            if all_active:
                st.divider()
                st.markdown(
                    f'<div style="font-size:.72rem;color:{TEXT_2};letter-spacing:2px;'
                    f'font-weight:600;padding:4px 0 8px;">YOUR ALL HANDS</div>',
                    unsafe_allow_html=True,
                )
                for c, ev in all_active:
                    try:
                        label = datetime.strptime(ev["event_date"], "%Y-%m-%d").strftime("%B %Y")
                    except Exception:
                        label = _fmt_cycle(c)
                    if st.button(label, key=f"home_nav_{c}", use_container_width=True):
                        st.session_state["current_cycle"] = c
                        st.rerun()
        render_home()
        return

    # ── Event page ─────────────────────────────────────────────
    ev = db.get_event(cycle)
    if not ev or not ev.get("event_date"):
        # Event was reset — go back home
        st.session_state.pop("current_cycle", None)
        st.rerun()
        return

    section = render_sidebar(cycle)

    st.markdown(
        f'<div style="padding:4px 0 12px;">'
        f'<span style="font-size:1.5rem;font-weight:800;color:{TEXT_1};">EMEA All Hands</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Due reminders banner ────────────────────────────────────
    due = []
    for r in ev.get("reminders", []):
        if r.get("status") == "approved" and r.get("scheduled_date") and r.get("scheduled_time"):
            try:
                sched_dt = datetime.strptime(
                    f"{r['scheduled_date']} {r['scheduled_time']}", "%Y-%m-%d %H:%M"
                )
                if sched_dt <= datetime.now():
                    due.append(r)
            except Exception:
                pass
    if due:
        names = ", ".join(r["name"] for r in due)
        ban1, ban2 = st.columns([5, 1])
        ban1.markdown(
            f'<div class="smart-alert" style="background:#ef444422;border-color:#ef444444;color:#F87171;">'
            f'🔔 <strong>{len(due)} reminder{"s" if len(due) != 1 else ""} ready to send:</strong> {names}</div>',
            unsafe_allow_html=True,
        )
        if ban2.button("Go to Reminders →", key="_due_banner_btn", use_container_width=True):
            st.session_state["_nav_goto"] = 4
            st.rerun()

    if section == NAV_ITEMS[0]:
        render_event_setup(cycle)
    elif section == NAV_ITEMS[1]:
        render_contributors(cycle)
    elif section == NAV_ITEMS[2]:
        render_communications(cycle)
    elif section == NAV_ITEMS[3]:
        render_new_joiners(cycle)
    elif section == NAV_ITEMS[4]:
        render_auto_reminders(cycle)
    elif section == NAV_ITEMS[5]:
        render_post_event(cycle)
    elif section == NAV_ITEMS[6]:
        render_notion_folder(cycle)


if __name__ == "__main__":
    main()
