import pytest
from bot.utils.time_parse_paginate import safe_parse_date, format_discord_timestamp, format_log_entry


# --- safe_parse_date ---
@pytest.mark.utils
@pytest.mark.parametrize("date_str,expected", [
    ("2025-01-01", "2025-01-01"),   # ISO format
    ("2025/01/01", "2025-01-01"),   # Slash format
    ("01/01/2025", "2025-01-01"),   # European format
    ("13/2025/01", None),           # Invalid month/day order
    ("not-a-date", None),           # Not a date
])
def test_safe_parse_date_formats(date_str, expected):
    """Ensure safe_parse_date handles valid and invalid date formats."""
    assert safe_parse_date(date_str) == expected


# --- format_discord_timestamp ---
@pytest.mark.utils
@pytest.mark.parametrize("input_str,expected_contains", [
    ("2025-01-01T12:00:00", "<t:"),   # Valid ISO date
    ("invalid-date", "invalid-date"), # Invalid date string
])
def test_format_discord_timestamp_cases(input_str, expected_contains):
    """Ensure format_discord_timestamp formats valid dates and passes through invalid strings."""
    result = format_discord_timestamp(input_str)
    assert expected_contains in result


# --- format_log_entry ---
@pytest.mark.utils
@pytest.mark.basic
def test_format_log_entry_content():
    """Ensure log entries format correctly with action, user, timestamp, and description."""
    entry = format_log_entry(
        log_action="edit",
        performed_by="1234",
        performed_at="2025-01-01 10:00:00.000000",
        log_description="Updated name",
        label="Event"
    )
    assert "**Event:** **Edit**" in entry
    assert "Updated name" in entry
    assert "<@1234>" in entry
    assert "<t:" in entry  # Discord timestamp format
