"""
Slack operations — channel creation, invites, messaging, user directory.

Requires SLACK_BOT_TOKEN in st.secrets.
Bot needs scopes: channels:manage, channels:write.invites, chat:write, groups:write,
                  users:read, users:read.email
"""

import ssl
import streamlit as st
from typing import Optional, List


def _ssl_context():
    """Build an SSL context using certifi's CA bundle (fixes macOS certificate issues)."""
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        return ctx
    except ImportError:
        return ssl.create_default_context()


def _client():
    """Return a Slack WebClient or (None, error)."""
    try:
        from slack_sdk import WebClient
        token = st.secrets.get("SLACK_BOT_TOKEN", "")
        if not token:
            return None, "SLACK_BOT_TOKEN not set in .streamlit/secrets.toml"
        return WebClient(token=token, ssl=_ssl_context()), None
    except Exception as e:
        return None, str(e)


def _channel_exists(client, name: str) -> Optional[str]:
    """Check if a channel (public or private) already exists. Returns channel ID or None."""
    try:
        cursor = None
        while True:
            resp = client.conversations_list(
                types="public_channel,private_channel",
                limit=200,
                cursor=cursor,
            )
            for ch in resp.get("channels", []):
                if ch["name"] == name:
                    return ch["id"]
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    except Exception:
        pass
    return None


def create_channel(name: str, is_private: bool = True) -> dict:
    """
    Create a Slack channel. Returns {"ok", "channel_id", "channel_name", "error"}.
    """
    client, err = _client()
    if not client:
        return {"ok": False, "error": err}

    clean = name.lower().replace(" ", "-")[:80]
    try:
        existing = _channel_exists(client, clean)
        if existing:
            return {
                "ok": True,
                "channel_id": existing,
                "channel_name": clean,
                "note": "Channel already existed",
            }

        resp = client.conversations_create(name=clean, is_private=is_private)
        ch = resp["channel"]
        return {"ok": True, "channel_id": ch["id"], "channel_name": ch["name"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def invite_users(channel_id: str, user_ids: List[str]) -> dict:
    """Invite a list of Slack user IDs to a channel."""
    client, err = _client()
    if not client:
        return {"ok": False, "error": err}

    if not user_ids:
        return {"ok": True, "invited": 0}

    try:
        client.conversations_invite(channel=channel_id, users=",".join(user_ids))
        return {"ok": True, "invited": len(user_ids)}
    except Exception as e:
        msg = str(e)
        if "already_in_channel" in msg:
            return {"ok": True, "invited": 0, "note": "Already in channel"}
        return {"ok": False, "error": msg}


def post_message(channel: str, text: str) -> dict:
    """Post a message. channel can be a channel ID, #channel-name, or user ID."""
    client, err = _client()
    if not client:
        return {"ok": False, "error": err}

    target = channel.strip()

    if target.startswith("#"):
        target = target[1:]

    try:
        resp = client.chat_postMessage(channel=target, text=text)
        return {"ok": True, "ts": resp["ts"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_dm(user_id: str, text: str) -> dict:
    """Open a DM conversation with a user and send a message."""
    client, err = _client()
    if not client:
        return {"ok": False, "error": err}

    try:
        dm = client.conversations_open(users=[user_id])
        dm_channel = dm["channel"]["id"]
        resp = client.chat_postMessage(channel=dm_channel, text=text)
        return {"ok": True, "ts": resp["ts"], "channel": dm_channel}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def lookup_user_by_email(email: str) -> Optional[str]:
    """Resolve an email to a Slack user ID."""
    client, err = _client()
    if not client:
        return None
    try:
        resp = client.users_lookupByEmail(email=email)
        return resp["user"]["id"]
    except Exception:
        return None


def is_token_configured() -> bool:
    """Check if a real Slack bot token is set (not the placeholder)."""
    token = st.secrets.get("SLACK_BOT_TOKEN", "")
    return bool(token) and token != "xoxb-your-token-here"


def save_as_slack_draft_background(channel: str, message: str) -> None:
    """
    Fire-and-forget: invoke the Claude CLI to save `message` as a Slack draft
    in `channel` via the Slack MCP tool.  Runs as a detached subprocess so it
    never blocks the Streamlit UI.  Silently skips if `claude` is not on PATH.
    Logs output to draft_claude.log for debugging.
    """
    import subprocess
    import shutil
    import os

    claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not os.path.isfile(claude_bin):
        return

    prompt = (
        f"Save this message as a Slack draft in #{channel} using the "
        f"mcp__slack__slack_send_message_draft tool. "
        f"If you get a draft_already_exists error, respond with exactly 'DRAFT_ALREADY_EXISTS' "
        f"and do nothing else — the user will edit the existing draft directly in Slack. "
        f"Do NOT post or schedule the message.\n\n"
        f"{message}"
    )
    log_path = os.path.join(os.path.dirname(__file__), "draft_claude.log")
    with open(log_path, "a") as log_f:
        subprocess.Popen(
            [claude_bin, "--dangerously-skip-permissions", "-p", prompt],
            stdout=log_f,
            stderr=log_f,
        )


def schedule_reminder_background(channel: str, message: str, date_str: str, time_str: str) -> None:
    """
    Fire-and-forget: invoke the Claude CLI to schedule `message` in `channel`
    at `date_str` `time_str` (CET) via the Slack MCP tool.
    Silently skips if the draft already exists or `claude` is not on PATH.
    """
    import subprocess
    import shutil
    import os

    claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not os.path.isfile(claude_bin):
        return

    prompt = (
        f"Schedule this Slack message for channel #{channel} on {date_str} at {time_str} CET (Europe/Madrid).\n"
        f"Steps:\n"
        f"1. Use mcp__slack__slack_search_channels to find the channel ID for #{channel}.\n"
        f"2. Convert {date_str} {time_str} CET to a Unix timestamp.\n"
        f"3. Use mcp__slack__slack_schedule_message with the channel ID, message, and Unix timestamp.\n"
        f"If it fails because a scheduled message already exists, respond with 'ALREADY_SCHEDULED' "
        f"and do nothing else — the user will manage it from Slack Drafts & Sent.\n\n"
        f"Message:\n{message}"
    )
    log_path = os.path.join(os.path.dirname(__file__), "draft_claude.log")
    with open(log_path, "a") as log_f:
        subprocess.Popen(
            [claude_bin, "--dangerously-skip-permissions", "-p", prompt],
            stdout=log_f,
            stderr=log_f,
        )


def save_to_notion_background(ev_date: str, pres_title: str, pres_url: str) -> None:
    """
    Fire-and-forget: invoke the Claude CLI to append the presentation
    to the EMEA All Hands Notion page via the Notion MCP tool.
    """
    import subprocess
    import shutil
    import os

    claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not os.path.isfile(claude_bin):
        return

    notion_page_url = "https://app.notion.com/p/affirm/EMEA-All-Hands-10d40e54ae38807eb40fd687c7f7a306"

    prompt = (
        f"Add this EMEA All Hands presentation to the Notion page at {notion_page_url}.\n"
        f"Steps:\n"
        f"1. Use mcp__notion__notion-fetch to read the current page and understand its format.\n"
        f"2. Use mcp__notion__notion-update-page to prepend a new entry at the top of the page with:\n"
        f"   - Date: {ev_date}\n"
        f"   - Title: {pres_title}\n"
        f"   - Link: {pres_url}\n"
        f"Match the existing format (table row or bullet) on the page exactly.\n"
        f"Do NOT create a new page — update the existing one only."
    )
    log_path = os.path.join(os.path.dirname(__file__), "draft_claude.log")
    with open(log_path, "a") as log_f:
        subprocess.Popen(
            [claude_bin, "--dangerously-skip-permissions", "-p", prompt],
            stdout=log_f,
            stderr=log_f,
        )


def list_workspace_users() -> dict:
    """
    Fetch all active, non-bot users from the Slack workspace.
    Returns {"ok": bool, "users": [...], "error": str}.
    Each user dict has: id, name, real_name, email, display_name.
    """
    client, err = _client()
    if not client:
        return {"ok": False, "users": [], "error": err}

    try:
        all_users = []
        cursor = None
        while True:
            resp = client.users_list(limit=200, cursor=cursor)
            for u in resp.get("members", []):
                if u.get("deleted") or u.get("is_bot") or u.get("id") == "USLACKBOT":
                    continue
                profile = u.get("profile", {})
                all_users.append({
                    "id": u["id"],
                    "name": u.get("name", ""),
                    "real_name": profile.get("real_name", u.get("real_name", "")),
                    "email": profile.get("email", ""),
                    "display_name": profile.get("display_name", ""),
                })
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        all_users.sort(key=lambda u: u["real_name"].lower())
        return {"ok": True, "users": all_users}
    except Exception as e:
        return {"ok": False, "users": [], "error": str(e)}
