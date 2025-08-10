from typing import Optional
from datetime import datetime, timezone

def now_iso() -> str:
    """Current UTC time in ISO 8601 format with timezone offset."""
    return datetime.now(timezone.utc).isoformat()

def now_unix() -> int:
    """Current UTC time as Unix timestamp (int)."""
    return int(datetime.now(timezone.utc).timestamp())

def format_discord_timestamp(iso_str: str, style: str = "F") -> str:
    """
    Format an ISO 8601 datetime string to a Discord timestamp token.
    Returns the original string if parsing fails.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        unix_ts = int(dt.timestamp())
        return f"<t:{unix_ts}:{style}>"
    except Exception:
        return iso_str

def format_log_entry(
    log_action: str,
    performed_by: str,
    performed_at: str,
    log_description: Optional[str] = None,
    label: Optional[str] = None
) -> str:
    """
    Format a generic log entry for display in embeds or paginated lists.
    `performed_at` expected as "%Y-%m-%d %H:%M:%S.%f" (falls back to raw string).
    """
    try:
        dt = datetime.strptime(performed_at, "%Y-%m-%d %H:%M:%S.%f")
        ts = f"<t:{int(dt.timestamp())}:f>"
    except Exception:
        ts = performed_at

    label_prefix = f"**{label}:** " if label else ""
    description_part = f" — {log_description}" if log_description else ""
    return f"{label_prefix}**{log_action.capitalize()}** by <@{performed_by}> at {ts}{description_part}"