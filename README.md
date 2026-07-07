# Affirm EMEA All Hands — Automation Engine

Streamlit app that automates the EMEA All Hands operational lifecycle:
Google Drive file management, Slack channel orchestration, and presenter coordination.

## Quick start

```bash
# 1. Install Python 3.11+ then:
cd emea-all-hands-command-center
pip install -r requirements.txt

# 2. Set up secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your Slack bot token

# 3. Set up Google OAuth (one-time)
# Download an OAuth 2.0 Client ID (Desktop app) JSON from Google Cloud Console
# and save it as .streamlit/client_secret.json
# The app will open a browser for you to log in on first run.

# 4. Run
streamlit run app.py
```

## Architecture

| File | Purpose |
|---|---|
| `app.py` | Main UI — three tabs (Setup & Folders, Presenter Comms, Event Day) |
| `db.py` | SQLite persistence for events, contributors, status log |
| `drive.py` | Google Drive API — folder creation, deck copy, blank slides (OAuth Desktop flow) |
| `slack_ops.py` | Slack SDK — channel creation, invites, messaging |
| `templates.py` | Verbatim Slack message templates |

## Secrets required

| Key | Description |
|---|---|
| `SLACK_BOT_TOKEN` | Slack bot token (`xoxb-...`). Scopes: `channels:manage`, `channels:write.invites`, `chat:write`, `groups:write`, `users:read`, `users:read.email` |

### Google OAuth setup

This app uses **OAuth 2.0 (Desktop)**, not a service account. Your own Google account
(e.g. Affirm login) is used so you have full access to Shared Drives.

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth 2.0 Client ID** (application type: **Desktop app**).
3. Download the JSON and save it as `.streamlit/client_secret.json`.
4. Enable the **Drive API** and **Slides API** in your project.
5. On first run, the app opens a browser for you to log in. The token is cached in `.streamlit/token.json`.

## Workflow

1. **Setup & Folders** — Enter event details, run Google Drive automation (create folder, copy deck, create blank slides), create Slack contributor channel, add/invite contributors.
2. **Presenter Comms** — Preview and approve the Welcome message and 1-Week Reminder before posting to the contributor channel.
3. **Event Day** — Preview and approve the Day-of Reminder and Post-Event Follow-Up before posting to `#online-monthly-emea-all-hands`.

Every Slack message requires explicit **Approve & Send** before it is posted (human-in-the-loop).
