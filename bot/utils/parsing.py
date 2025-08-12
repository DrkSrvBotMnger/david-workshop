# bot/utils/parsing.py
import json
from typing import Optional
from bot.config import SUPPORTED_FIELDS

def safe_parse_date(date_str: str) -> Optional[str]:
    """Attempts to parse a date string into YYYY-MM-DD. Returns None if invalid."""
    from datetime import datetime
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]
    s = (date_str or "").strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def parse_required_fields(input_fields_json: Optional[str]) -> list[str]:
    """Return ordered list of required fields Action definitions (subset of SUPPORTED_FIELDS)."""
    if not input_fields_json:
        return []
    try:
        fields = json.loads(input_fields_json)
    except Exception:
        return []
    out: list[str] = []
    for f in fields:
        name = str(f).strip().lower()
        if name in SUPPORTED_FIELDS and name not in out:
            out.append(name)
    return out

def parse_help_texts(input_help_text: Optional[str], fields: list[str]) -> dict[str, str]:
    """
    Turn the ActionEvent.input_help_text JSON (a list) into a dict:
      {"general": "...", <per-field...>}
    The list is expected as: [general, <one per field in `fields` order>]
    Missing/short lists are handled gracefully.
    """
    result: dict[str, str] = {"general": ""}
    if not input_help_text:
        return result
    try:
        items = json.loads(input_help_text)
    except Exception:
        return result

    if not isinstance(items, list) or not items:
        return result

    result["general"] = str(items[0]).strip() if items and items[0] is not None else ""
    per_field = items[1:]
    for i, fname in enumerate(fields):
        if i < len(per_field):
            val = per_field[i]
            result[fname] = str(val).strip() if val is not None else ""
        else:
            result[fname] = ""
    return result

def parse_message_link(message_link: str) -> tuple[int, int]:
    """
    Parse a Discord message link into (channel_id, message_id).
    Raises ValueError if format is invalid.
    """
    try:
        parts = message_link.strip().split("/")
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
        return channel_id, message_id
    except (IndexError, ValueError):
        raise ValueError("Invalid Discord message link format.")