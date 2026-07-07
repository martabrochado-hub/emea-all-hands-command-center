"""
Export generators — plain text, HTML, and PDF summaries for EMEA All Hands events.
"""

import re
from datetime import datetime


def _strip_emojis(text: str) -> str:
    return re.sub(
        r"[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F"
        r"\U0001FA00-\U0001FAFF\U00002600-\U000026FF]+",
        "",
        text,
    )


def _status_label(status: str) -> str:
    return status.replace("_", " ").title()


# ── Plain Text ─────────────────────────────────────────────────

def generate_plain_text(event: dict, contributors: list, messages: dict) -> str:
    lines: list[str] = []
    cycle = event.get("cycle", "")

    lines.append("=" * 60)
    lines.append(f"EMEA ALL HANDS — {cycle} — EVENT SUMMARY")
    lines.append("=" * 60)
    lines.append("")

    lines.append("EVENT DETAILS")
    lines.append("-" * 40)
    for label, key in [
        ("Month", "cycle"),
        ("Date", "event_date"),
        ("Time", "event_time"),
        ("UK Time", "uk_time"),
        ("Zoom Link", "zoom_link"),
        ("Presentation Title", "presentation_title"),
        ("Presentation Link", "presentation_link"),
        ("Recording Link", "recording_link"),
        ("Recording Passcode", "recording_passcode"),
        ("Feedback Survey", "feedback_survey_link"),
        ("EMEA Folder", "emea_folder_link"),
        ("Recordings Folder", "emea_recordings_folder_link"),
        ("Contributor Deadline", "contributor_deadline"),
        ("Internal Owners", "internal_owners"),
        ("Support Contacts", "support_contacts"),
    ]:
        val = event.get(key, "")
        if val:
            lines.append(f"  {label}: {val}")
    lines.append("")

    prep = event.get("prep_checklist", [])
    if prep:
        lines.append("PREPARATION CHECKLIST")
        lines.append("-" * 40)
        for item in prep:
            status = _status_label(item.get("status", "not_started"))
            owner = f" [{item['owner']}]" if item.get("owner") else ""
            lines.append(f"  [{status}] {item['task']}{owner}")
            if item.get("notes"):
                lines.append(f"    Notes: {item['notes']}")
        lines.append("")

    if contributors:
        lines.append("CONTRIBUTORS")
        lines.append("-" * 40)
        for c in contributors:
            avail = "Yes" if c.get("availability_confirmed") else "No"
            pres = "Yes" if c.get("presentation_confirmed") else "No"
            lines.append(f"  {c['name']} — {c.get('team_function') or 'N/A'}")
            lines.append(f"    Topic: {c.get('topic') or 'TBD'}")
            lines.append(f"    Available: {avail} | Presentation Ready: {pres}")
            if c.get("notes"):
                lines.append(f"    Notes: {c['notes']}")
        lines.append("")

    ops = event.get("ops_checklist", [])
    if ops:
        for phase_label, phase_key in [
            ("DAY-OF OPERATIONS", "day_of"),
            ("POST-EVENT OPERATIONS", "post_event"),
        ]:
            items = [i for i in ops if i.get("phase") == phase_key]
            if items:
                lines.append(phase_label)
                lines.append("-" * 40)
                for item in items:
                    status = _status_label(item.get("status", "not_started"))
                    lines.append(f"  [{status}] {item['task']}")
                    if item.get("notes"):
                        lines.append(f"    Notes: {item['notes']}")
                lines.append("")

    lines.append("GENERATED COMMUNICATIONS")
    lines.append("-" * 40)
    for label, key in [
        ("Contributor Channel Message", "contributor"),
        ("Pre-Event Reminder", "pre_event"),
        ("Post-Event Follow-Up", "post_event"),
    ]:
        msg = messages.get(key, "")
        if msg:
            lines.append(f"\n  {label}:")
            lines.append("  " + "~" * 36)
            for line in msg.split("\n"):
                lines.append(f"  {line}")
            lines.append("")

    lines.append("=" * 60)
    lines.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


# ── HTML ───────────────────────────────────────────────────────

def generate_html(event: dict, contributors: list, messages: dict) -> str:
    cycle = event.get("cycle", "")

    detail_rows = ""
    for label, key in [
        ("Month", "cycle"), ("Date", "event_date"), ("Time", "event_time"),
        ("UK Time", "uk_time"), ("Zoom Link", "zoom_link"),
        ("Presentation Title", "presentation_title"),
        ("Presentation Link", "presentation_link"),
        ("Recording Link", "recording_link"),
        ("Recording Passcode", "recording_passcode"),
        ("Feedback Survey", "feedback_survey_link"),
        ("Contributor Deadline", "contributor_deadline"),
        ("Internal Owners", "internal_owners"),
        ("Support Contacts", "support_contacts"),
    ]:
        val = event.get(key, "")
        if val:
            cell = f'<a href="{val}">{val}</a>' if val.startswith("http") else val
            detail_rows += f"<tr><td><strong>{label}</strong></td><td>{cell}</td></tr>\n"

    prep_rows = ""
    for item in event.get("prep_checklist", []):
        status = item.get("status", "not_started")
        cls = {"done": "done", "in_progress": "progress", "blocked": "blocked"}.get(
            status, "not-started"
        )
        prep_rows += (
            f"<tr><td><span class='badge {cls}'>{_status_label(status)}</span></td>"
            f"<td>{item['task']}</td>"
            f"<td>{item.get('owner', '')}</td>"
            f"<td>{item.get('notes', '')}</td></tr>\n"
        )

    contrib_rows = ""
    for c in contributors:
        a = "\u2713" if c.get("availability_confirmed") else "\u2014"
        p = "\u2713" if c.get("presentation_confirmed") else "\u2014"
        contrib_rows += (
            f"<tr><td>{c['name']}</td>"
            f"<td>{c.get('team_function', '')}</td>"
            f"<td>{c.get('topic', '')}</td>"
            f"<td style='text-align:center'>{a}</td>"
            f"<td style='text-align:center'>{p}</td>"
            f"<td>{c.get('notes', '')}</td></tr>\n"
        )

    ops = event.get("ops_checklist", [])
    dayof_rows, post_rows = "", ""
    for item in ops:
        status = item.get("status", "not_started")
        cls = {"done": "done", "in_progress": "progress", "blocked": "blocked"}.get(
            status, "not-started"
        )
        row = (
            f"<tr><td><span class='badge {cls}'>{_status_label(status)}</span></td>"
            f"<td>{item['task']}</td>"
            f"<td>{item.get('notes', '')}</td></tr>\n"
        )
        if item.get("phase") == "day_of":
            dayof_rows += row
        else:
            post_rows += row

    msg_html = ""
    for label, key in [
        ("Contributor Channel Message", "contributor"),
        ("Pre-Event Reminder", "pre_event"),
        ("Post-Event Follow-Up", "post_event"),
    ]:
        msg = messages.get(key, "")
        if msg:
            msg_html += (
                f"<div class='msg-card'><h3>{label}</h3>"
                f"<pre>{msg}</pre></div>\n"
            )

    no_contrib = (
        "<tr><td colspan='6' style='color:#94a3b8'>No contributors added</td></tr>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>EMEA All Hands \u2014 {cycle}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
body{{font-family:'Inter',sans-serif;background:#fff;color:#13131F;max-width:900px;margin:0 auto;padding:40px 24px}}
h1{{color:#0A0340;border-bottom:3px solid #4A4AF4;padding-bottom:12px}}
h2{{color:#4A4AF4;margin-top:36px}}
table{{width:100%;border-collapse:collapse;margin:16px 0}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid #e5e5e5;font-size:14px}}
th{{background:#f8f8fc;font-weight:600;color:#0A0340}}
.badge{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600}}
.badge.done{{background:#d1fae5;color:#065f46}}
.badge.progress{{background:#fef3c7;color:#92400e}}
.badge.blocked{{background:#fee2e2;color:#991b1b}}
.badge.not-started{{background:#f1f5f9;color:#475569}}
.msg-card{{background:#f8f8fc;border:1px solid #e5e5e5;border-radius:12px;padding:20px;margin:16px 0}}
.msg-card h3{{margin-top:0;color:#0A0340}}
.msg-card pre{{white-space:pre-wrap;font-family:'Inter',sans-serif;font-size:14px;line-height:1.6}}
.footer{{margin-top:48px;padding-top:16px;border-top:1px solid #e5e5e5;color:#94a3b8;font-size:12px}}
@media print{{body{{padding:20px}}}}
</style>
</head>
<body>
<h1>EMEA All Hands \u2014 {cycle}</h1>

<h2>Event Details</h2>
<table>{detail_rows}</table>

<h2>Preparation Checklist</h2>
<table>
<tr><th>Status</th><th>Task</th><th>Owner</th><th>Notes</th></tr>
{prep_rows}
</table>

<h2>Contributors</h2>
<table>
<tr><th>Name</th><th>Team</th><th>Topic</th><th>Available</th><th>Pres.&nbsp;Ready</th><th>Notes</th></tr>
{contrib_rows or no_contrib}
</table>

<h2>Day-of Operations</h2>
<table>
<tr><th>Status</th><th>Task</th><th>Notes</th></tr>
{dayof_rows}
</table>

<h2>Post-Event Operations</h2>
<table>
<tr><th>Status</th><th>Task</th><th>Notes</th></tr>
{post_rows}
</table>

<h2>Communications</h2>
{msg_html}

<div class="footer">
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; Affirm People Team
</div>
</body>
</html>"""


# ── PDF ────────────────────────────────────────────────────────

def generate_pdf_bytes(event: dict, contributors: list, messages: dict) -> bytes | None:
    """Return PDF bytes or None if fpdf2 is unavailable."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    cycle = event.get("cycle", "")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(10, 3, 64)
    pdf.cell(0, 14, f"EMEA All Hands - {cycle}", ln=True)
    pdf.ln(4)
    pdf.set_draw_color(74, 74, 244)
    pdf.set_line_width(1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    def _section(title: str):
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(74, 74, 244)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_text_color(19, 19, 31)

    def _kv(label: str, value: str):
        if not value:
            return
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(48, 7, f"{label}:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, _strip_emojis(str(value))[:90], ln=True)

    _section("Event Details")
    for label, key in [
        ("Date", "event_date"), ("Time", "event_time"), ("UK Time", "uk_time"),
        ("Zoom Link", "zoom_link"), ("Presentation", "presentation_title"),
        ("Deadline", "contributor_deadline"), ("Owners", "internal_owners"),
        ("Support", "support_contacts"),
    ]:
        _kv(label, event.get(key, ""))
    pdf.ln(4)

    _section("Preparation Checklist")
    for item in event.get("prep_checklist", []):
        status = _status_label(item.get("status", "not_started"))
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 6, f"[{status}]")
        pdf.set_font("Helvetica", "", 9)
        extra = f"  ({item['owner']})" if item.get("owner") else ""
        pdf.cell(0, 6, _strip_emojis(item["task"]) + extra, ln=True)
    pdf.ln(4)

    if contributors:
        _section("Contributors")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(248, 248, 252)
        widths = [42, 32, 46, 18, 18, 18]
        headers = ["Name", "Team", "Topic", "Avail.", "Pres.", "Slack"]
        for w, h in zip(widths, headers):
            pdf.cell(w, 7, h, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for c in contributors:
            vals = [
                c["name"][:18],
                (c.get("team_function") or "")[:14],
                (c.get("topic") or "")[:22],
                "Yes" if c.get("availability_confirmed") else "No",
                "Yes" if c.get("presentation_confirmed") else "No",
                "Yes" if c.get("slack_channel_created") else "No",
            ]
            for w, v in zip(widths, vals):
                pdf.cell(w, 6, v, border=1)
            pdf.ln()
        pdf.ln(4)

    ops = event.get("ops_checklist", [])
    if ops:
        for phase_title, phase_key in [
            ("Day-of Operations", "day_of"),
            ("Post-Event Operations", "post_event"),
        ]:
            items = [i for i in ops if i.get("phase") == phase_key]
            if items:
                _section(phase_title)
                for item in items:
                    status = _status_label(item.get("status", "not_started"))
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(30, 6, f"[{status}]")
                    pdf.set_font("Helvetica", "", 9)
                    pdf.cell(0, 6, _strip_emojis(item["task"]), ln=True)
                pdf.ln(4)

    pdf.add_page()
    _section("Communications")
    for label, key in [
        ("Contributor Channel Message", "contributor"),
        ("Pre-Event Reminder", "pre_event"),
        ("Post-Event Follow-Up", "post_event"),
    ]:
        msg = messages.get(key, "")
        if msg:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(10, 3, 64)
            pdf.cell(0, 8, label, ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(19, 19, 31)
            pdf.multi_cell(0, 5, _strip_emojis(msg))
            pdf.ln(2)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(
        0, 6,
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Affirm People Team",
        ln=True,
    )
    return bytes(pdf.output())
