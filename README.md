# Affirm People Ops Triage Bot

A Streamlit-powered internal tool that helps the Affirm People Team manage and automate responses to employee Slack messages about benefits, leave, payroll, immigration, and more.

## What it does

1. **Paste** an employee's Slack message
2. **Auto-classify** the topic and subtopic using multilingual keyword matching (EN, ES, CA, PL)
3. **Generate** a warm, policy-rich reply with three tone variations
4. **Enrich** with country-specific policies (Spain, UK, Poland)
5. **Preview** in a Slack-style UI, edit freely, then send or copy

## Quick start

```bash
cd emea-all-hands-command-center
pip install -r requirements.txt
streamlit run people_ops_triage.py --server.port 8503
```

Open http://localhost:8503 in your browser.

## Files

| File | Purpose |
|---|---|
| `people_ops_triage.py` | Main app — classification, reply generation, translations, UI |
| `slack_ops.py` | Slack API integration — send DMs and channel messages |
| `app.py` | EMEA All Hands Command Center (separate event management app) |
| `db.py` | SQLite persistence for the All Hands app |
| `templates.py` | Slack message templates for the All Hands app |
| `exports.py` | Export generators (TXT, HTML, PDF) for the All Hands app |
| `drive.py` | Google Drive integration (optional) |

## Key features

- **13+ topics, 50+ subtopics** — Leave, Benefits, Payroll, Immigration, Equity, Workplace, L&D, Company Policies, Offboarding, and more
- **Multilingual** — auto-detects English, Spanish, Catalan, and Polish; replies fully translated
- **Country-specific policies** — select Spain, UK, or Poland for local leave entitlements, benefits, and statutory details
- **Multi-question handling** — splits and classifies multiple questions in a single message
- **Three tone variations** — Friendly & Warm, Short & Efficient, Structured / Policy-Guided
- **Live Slack preview** — edits to the reply are reflected in real-time
- **Out-of-scope handling** — provides useful info even for non-People Ops topics (e.g., IT, events) with appropriate disclaimers
- **Analytics dashboard** — tracks question distribution by category
- **Knowledge base** — Workday tutorials, Luxmed enrollment, TA300/7p tax processes, and more

## Slack integration (optional)

To send messages directly from the app, add a valid bot token to `.streamlit/secrets.toml`:

```toml
SLACK_BOT_TOKEN = "xoxb-your-actual-bot-token"
```

Required bot scopes: `chat:write`, `users:read`, `users:read.email`, `im:write`.

## Requirements

- Python 3.11+
- `streamlit >= 1.45.0`
- `slack_sdk >= 3.34.0`
- See `requirements.txt` for full list

## Brand

Uses Affirm's color palette:
- Indigo: `#4A4AF4`
- Dark Indigo: `#0A0340`
- Light Indigo: `#9DADF9`
- Font: Axiforma (fallback: Inter, Arial)
