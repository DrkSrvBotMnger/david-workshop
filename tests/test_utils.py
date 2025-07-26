import pytest
import discord
from bot.utils import safe_parse_date, format_discord_timestamp, format_log_entry, EmbedPaginator


def test_safe_parse_date_valid_formats():
    assert safe_parse_date("2025-01-01") == "2025-01-01"
    assert safe_parse_date("2025/01/01") == "2025-01-01"
    assert safe_parse_date("01/01/2025") == "2025-01-01"


def test_safe_parse_date_invalid_format():
    assert safe_parse_date("13/2025/01") is None
    assert safe_parse_date("not-a-date") is None


def test_format_discord_timestamp_valid():
    from datetime import datetime
    iso = datetime(2025, 1, 1, 12, 0, 0).isoformat()
    result = format_discord_timestamp(iso)
    assert result.startswith("<t:")
    assert result.endswith(":F>") or result.endswith(":f>")


def test_format_discord_timestamp_invalid():
    assert format_discord_timestamp("invalid-date") == "invalid-date"


def test_format_log_entry():
    entry = format_log_entry(
        action="edit",
        performed_by="1234",
        timestamp="2025-01-01 10:00:00.000000",
        description="Updated name",
        label="Event"
    )
    assert "**Event:** **Edit**" in entry
    assert "Updated name" in entry
    assert "<@1234>" in entry


@pytest.mark.asyncio
async def test_embed_paginator_update_footer_sets_page_count():
    embeds = [discord.Embed(title=f"Test {i+1}") for i in range(3)]
    paginator = EmbedPaginator(embeds)

    for i, embed in enumerate(paginator.pages):
        assert embed.footer.text == f"Page {i + 1} of {len(embeds)}"