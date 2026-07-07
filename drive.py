"""
Google Drive, Slides & Forms operations — OAuth Desktop flow.

Uses your own Google account (e.g. Affirm login) so you have full access
to Shared Drives. On first run it opens a browser for login, then caches
the token locally in .streamlit/token.json.

Setup:
  1. In Google Cloud Console, create an OAuth 2.0 Client ID (Desktop app).
  2. Download the client JSON and save as .streamlit/client_secret.json
  3. Enable Drive API, Slides API, and Google Forms API.
  4. Run the app — it will open a browser to log in once.
"""

import json
import os
import re

SLIDES_MIME = "application/vnd.google-apps.presentation"
FOLDER_MIME = "application/vnd.google-apps.folder"

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
]

FORMS_SCOPES = DRIVE_SCOPES + [
    "https://www.googleapis.com/auth/forms.body",
]

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_CLIENT_SECRET = os.path.join(_APP_DIR, ".streamlit", "client_secret.json")
_TOKEN_FILE = os.path.join(_APP_DIR, ".streamlit", "token.json")
_TOKEN_FILE_FORMS = os.path.join(_APP_DIR, ".streamlit", "token_forms.json")


def _get_creds(scopes=None, token_file=None):
    """Obtain OAuth credentials — from st.secrets (cloud) or local token file (dev)."""
    if scopes is None:
        scopes = DRIVE_SCOPES
    if token_file is None:
        token_file = _TOKEN_FILE

    try:
        import streamlit as st
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        # Cloud deployment: load token from st.secrets
        if "GOOGLE_TOKEN_JSON" in st.secrets:
            raw = st.secrets["GOOGLE_TOKEN_JSON"]
            token_info = json.loads(raw) if isinstance(raw, str) else dict(raw)
            creds = Credentials.from_authorized_user_info(token_info, scopes)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds, None

        # Local dev: file-based OAuth flow
        if not os.path.exists(_CLIENT_SECRET):
            return None, (
                "OAuth not configured. Download your client_secret.json from "
                "Google Cloud Console and place it at:\n"
                f"  {_CLIENT_SECRET}\n"
                "See the README for instructions."
            )

        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(_CLIENT_SECRET, scopes)
                creds = flow.run_local_server(port=8090, open_browser=True)
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        return creds, None

    except Exception as e:
        return None, str(e)


def _get_service(api="drive", version="v3"):
    """Build a Google API service (Drive/Slides use drive token, Forms uses its own)."""
    from googleapiclient.discovery import build

    if api == "forms":
        creds, err = _get_creds(scopes=FORMS_SCOPES, token_file=_TOKEN_FILE_FORMS)
    else:
        creds, err = _get_creds(scopes=DRIVE_SCOPES, token_file=_TOKEN_FILE)

    if not creds:
        return None, err
    try:
        svc = build(api, version, credentials=creds, cache_discovery=False)
        return svc, None
    except Exception as e:
        return None, str(e)


def _folder_exists(service, parent_id, name):
    """Return folder ID if a child folder with this name already exists."""
    q = (
        "'{pid}' in parents and name = '{n}' "
        "and mimeType = '{m}' and trashed = false"
    ).format(pid=parent_id, n=name, m=FOLDER_MIME)
    resp = (
        service.files()
        .list(q=q, fields="files(id)", spaces="drive",
              supportsAllDrives=True, includeItemsFromAllDrives=True)
        .execute()
    )
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def create_folder(parent_id, name):
    """
    Create a folder inside parent_id.
    Returns {"ok": bool, "folder_id": str, "url": str, "error": str}.
    """
    svc, err = _get_service("drive", "v3")
    if not svc:
        return {"ok": False, "error": err}

    try:
        existing = _folder_exists(svc, parent_id, name)
        if existing:
            url = "https://drive.google.com/drive/folders/" + existing
            return {"ok": True, "folder_id": existing, "url": url, "note": "Already existed"}

        meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        folder = (
            svc.files()
            .create(body=meta, fields="id", supportsAllDrives=True)
            .execute()
        )
        fid = folder["id"]
        url = "https://drive.google.com/drive/folders/" + fid
        return {"ok": True, "folder_id": fid, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def copy_presentation(source_id, dest_folder_id, new_name):
    """
    Copy a Google Slides file into dest_folder_id with new_name.
    Returns {"ok": bool, "file_id": str, "url": str, "error": str}.
    """
    svc, err = _get_service("drive", "v3")
    if not svc:
        return {"ok": False, "error": err}

    try:
        body = {"name": new_name, "parents": [dest_folder_id]}
        copied = (
            svc.files()
            .copy(fileId=source_id, body=body, fields="id", supportsAllDrives=True)
            .execute()
        )
        fid = copied["id"]
        url = "https://docs.google.com/presentation/d/" + fid + "/edit"
        return {"ok": True, "file_id": fid, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_blank_slides(dest_folder_id, name):
    """
    Create a new blank Google Slides file in dest_folder_id.
    Returns {"ok": bool, "file_id": str, "url": str, "error": str}.
    """
    svc, err = _get_service("drive", "v3")
    if not svc:
        return {"ok": False, "error": err}

    try:
        meta = {"name": name, "mimeType": SLIDES_MIME, "parents": [dest_folder_id]}
        f = (
            svc.files()
            .create(body=meta, fields="id", supportsAllDrives=True)
            .execute()
        )
        fid = f["id"]
        url = "https://docs.google.com/presentation/d/" + fid + "/edit"
        return {"ok": True, "file_id": fid, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_survey(event_date: str, location: str, folder_id: str = None):
    """
    Create a Google Form feedback survey and optionally move it into folder_id.
    Returns {"ok": bool, "form_id": str, "url": str, "error": str}.
    """
    svc, err = _get_service("forms", "v1")
    if not svc:
        return {"ok": False, "error": err}

    title = f"EMEA All Hands Feedback — {event_date} ({location})"

    try:
        form = svc.forms().create(body={
            "info": {"title": title}
        }).execute()
        form_id = form["formId"]

        questions = [
            {
                "createItem": {
                    "item": {
                        "title": "How would you rate the overall quality of this All Hands?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "scaleQuestion": {
                                    "low": 1, "high": 5,
                                    "lowLabel": "Poor",
                                    "highLabel": "Excellent",
                                }
                            }
                        }
                    },
                    "location": {"index": 0}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "How relevant was the content to your role?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "scaleQuestion": {
                                    "low": 1, "high": 5,
                                    "lowLabel": "Not relevant",
                                    "highLabel": "Very relevant",
                                }
                            }
                        }
                    },
                    "location": {"index": 1}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "How was the pacing and length of the session?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": "Too short"},
                                        {"value": "Just right"},
                                        {"value": "Too long"},
                                    ]
                                }
                            }
                        }
                    },
                    "location": {"index": 2}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "What did you enjoy most about this All Hands?",
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {"paragraph": True}
                            }
                        }
                    },
                    "location": {"index": 3}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "What could we improve for next time?",
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {"paragraph": True}
                            }
                        }
                    },
                    "location": {"index": 4}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "Any other comments or suggestions?",
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {"paragraph": True}
                            }
                        }
                    },
                    "location": {"index": 5}
                }
            },
        ]

        svc.forms().batchUpdate(
            formId=form_id,
            body={"requests": questions}
        ).execute()

        url = f"https://docs.google.com/forms/d/{form_id}/viewform"

        # Move form into the event folder if provided
        if folder_id:
            try:
                drive_svc, _ = _get_service("drive", "v3")
                if drive_svc:
                    f = drive_svc.files().get(
                        fileId=form_id, fields="parents", supportsAllDrives=True
                    ).execute()
                    current_parents = ",".join(f.get("parents", []))
                    drive_svc.files().update(
                        fileId=form_id,
                        addParents=folder_id,
                        removeParents=current_parents,
                        fields="id,parents",
                        supportsAllDrives=True,
                    ).execute()
            except Exception:
                pass  # form created OK even if move fails

        return {"ok": True, "form_id": form_id, "url": url}

    except Exception as e:
        return {"ok": False, "error": str(e)}


def extract_file_id(url):
    """Pull a Google Drive/Slides file ID from a URL."""
    patterns = [
        r"/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/folders/([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return url.strip()


def _nj_title(period_label: str) -> str:
    base = "Welcome to Affirm! 🎉"
    return f"{base}\n{period_label}" if period_label else base


def _nj_body(people: list) -> str:
    if not people:
        return "No new joiners in this period."
    lines = []
    for p in people:
        flag     = p.get("flag", "🌍")
        name     = p.get("name", "")
        title    = p.get("title", "")
        location = p.get("location", "")
        lines.append(f"{flag}  {name}")
        details = "  ·  ".join(x for x in [title, location] if x)
        if details:
            lines.append(f"    {details}")
        lines.append("")
    return "\n".join(lines).rstrip()


def update_new_joiners_slide(presentation_id: str, people: list, period_label: str = "") -> dict:
    """
    Delete any existing 'EMEA New Joiners' slides, then recreate them grouped
    by country with up to 8 people per slide (4-column × 2-row grid, Slide-29 style).
    Returns {"ok": bool, "action": str, "slides_created": int, "error": str}.
    """
    svc, err = _get_service("slides", "v1")
    if not svc:
        return {"ok": False, "error": err}

    try:
        import uuid as _uuid
        from collections import defaultdict

        pres   = svc.presentations().get(presentationId=presentation_id).execute()
        slides = pres.get("slides", [])

        # ── Layout constants ─────────────────────────────────────────
        BLUE          = {"red": 0.2902, "green": 0.2902, "blue": 0.9804}
        SW            = 9144000          # slide width  (EMU)
        COLS          = 4
        MAX_PER_SLIDE = 8
        COL_W         = SW // COLS       # 2,286,000 EMU
        CARD_W        = 2_000_000
        CARD_H        =   550_000
        ROW_Y         = [1_350_000, 3_100_000]

        FLAG_COUNTRY  = {
            "🇪🇸": "Spain",
            "🇵🇱": "Poland",
            "🇬🇧": "United Kingdom",
            "🇳🇱": "Netherlands",
            "🇩🇪": "Germany",
            "🇫🇷": "France",
            "🇮🇹": "Italy",
        }
        COUNTRY_ORDER = ["Spain", "United Kingdom", "Netherlands", "Poland",
                         "Germany", "France", "Italy"]

        # ── Find existing NJ slides ───────────────────────────────────
        def _is_nj_slide(slide):
            for elem in slide.get("pageElements", []):
                shape = elem.get("shape", {})
                raw = "".join(
                    te.get("textRun", {}).get("content", "")
                    for te in shape.get("text", {}).get("textElements", [])
                ).lower()
                if "emea new joiners" in raw or (
                    shape.get("placeholder", {}).get("type") == "TITLE"
                    and any(kw in raw for kw in ("new joiner", "welcome", "new hire"))
                ):
                    return True
            return False

        nj_ids = [s["objectId"] for s in slides if _is_nj_slide(s)]
        insertion_index = 1
        for i, s in enumerate(slides):
            if s["objectId"] in nj_ids:
                insertion_index = i
                break

        # Delete old NJ slides first (separate API call so indices are clean)
        if nj_ids:
            svc.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": [{"deleteObject": {"objectId": sid}} for sid in nj_ids]},
            ).execute()

        # ── Group people by country ───────────────────────────────────
        by_country: dict = defaultdict(list)
        for p in people:
            flag    = p.get("flag", "🌍")
            country = FLAG_COUNTRY.get(flag, p.get("location", "Other"))
            by_country[country].append(p)

        sorted_countries = sorted(
            by_country.keys(),
            key=lambda c: (
                COUNTRY_ORDER.index(c) if c in COUNTRY_ORDER else len(COUNTRY_ORDER), c
            ),
        )

        # ── Builder helpers ───────────────────────────────────────────
        def _box(sid, oid, x, y, w, h):
            return {"createShape": {
                "objectId": oid, "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": sid,
                    "size": {
                        "width":  {"magnitude": w, "unit": "EMU"},
                        "height": {"magnitude": h, "unit": "EMU"},
                    },
                    "transform": {"scaleX": 1, "scaleY": 1,
                                  "translateX": x, "translateY": y,
                                  "unit": "EMU"},
                },
            }}

        def _txt_style(oid, start, end, bold=False, size_pt=7, color=None):
            style  = {
                "fontFamily": "Montserrat",
                "fontSize": {"magnitude": size_pt, "unit": "PT"},
                "bold": bold,
            }
            fields = "fontFamily,fontSize,bold"
            if color:
                style["foregroundColor"] = {"opaqueColor": {"rgbColor": color}}
                fields += ",foregroundColor"
            tr = ({"type": "ALL"} if (start == 0 and end is None)
                  else {"type": "FIXED_RANGE", "startIndex": start, "endIndex": end})
            return {"updateTextStyle": {"objectId": oid, "textRange": tr,
                                        "style": style, "fields": fields}}

        def _center(oid):
            return {"updateParagraphStyle": {
                "objectId": oid, "textRange": {"type": "ALL"},
                "style": {"alignment": "CENTER"}, "fields": "alignment",
            }}

        def _build_slide(sid, country, country_flag, batch, idx):
            reqs = [{"createSlide": {"objectId": sid, "insertionIndex": idx}}]

            # "EMEA All Hands" — small, blue
            hid = "nj_hdr_" + _uuid.uuid4().hex[:8]
            reqs += [
                _box(sid, hid, 1143000, 342900, 6858000, 250000),
                {"insertText": {"objectId": hid, "text": "EMEA All Hands", "insertionIndex": 0}},
                _txt_style(hid, 0, None, size_pt=7, color=BLUE),
                _center(hid),
            ]

            # "EMEA New Joiners — Country Flag" — large subtitle
            subtitle = f"EMEA New Joiners  {country_flag}  {country}"
            sub_id   = "nj_sub_" + _uuid.uuid4().hex[:8]
            reqs += [
                _box(sid, sub_id, 1143000, 610000, 6858000, 620000),
                {"insertText": {"objectId": sub_id, "text": subtitle, "insertionIndex": 0}},
                _txt_style(sub_id, 0, None, size_pt=20),
                _center(sub_id),
            ]

            # Period / date
            if period_label:
                did = "nj_date_" + _uuid.uuid4().hex[:8]
                reqs += [
                    _box(sid, did, 0, 981600, SW, 220000),
                    {"insertText": {"objectId": did, "text": period_label, "insertionIndex": 0}},
                    _txt_style(did, 0, None, size_pt=8),
                ]

            # Person cards — 4-column × 2-row grid
            for i, p in enumerate(batch):
                col  = i % COLS
                row  = i // COLS
                x    = col * COL_W + (COL_W - CARD_W) // 2
                y    = ROW_Y[row]

                name     = p.get("name", "")
                title    = p.get("title", "")
                flag     = p.get("flag", "🌍")
                location = p.get("location", "")
                loc_line = f"{flag}  {location}" if location else flag
                text     = "\n".join(filter(None, [name, title, loc_line]))

                pid = "nj_p_" + _uuid.uuid4().hex[:8]
                reqs += [
                    _box(sid, pid, x, y, CARD_W, CARD_H),
                    {"insertText": {"objectId": pid, "text": text, "insertionIndex": 0}},
                    _txt_style(pid, 0, None, size_pt=7),
                    _txt_style(pid, 0, len(name), bold=True, size_pt=7),
                    _center(pid),
                ]

            return reqs

        # ── Build all slides ──────────────────────────────────────────
        all_requests   = []
        slides_created = 0
        slide_idx      = insertion_index

        for country in sorted_countries:
            group        = by_country[country]
            country_flag = next((f for f, c in FLAG_COUNTRY.items() if c == country), "🌍")
            for batch_start in range(0, len(group), MAX_PER_SLIDE):
                batch = group[batch_start : batch_start + MAX_PER_SLIDE]
                sid   = "nj_slide_" + _uuid.uuid4().hex[:12]
                all_requests += _build_slide(sid, country, country_flag, batch, slide_idx)
                slide_idx      += 1
                slides_created += 1

        if all_requests:
            svc.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": all_requests},
            ).execute()

        action = "updated" if nj_ids else "created"
        return {"ok": True, "action": action, "slides_created": slides_created}

    except Exception as e:
        return {"ok": False, "error": str(e)}
