import pytest
from unittest.mock import MagicMock, patch
from bot.utils import is_admin_or_mod, MOD_ROLE_IDS


@pytest.mark.utils
@pytest.mark.access
@pytest.mark.asyncio
async def test_is_admin_or_mod_false_for_regular_user(guild_with_member):
    """User with no admin rights or mod roles should return False."""
    guild, member = guild_with_member
    member.guild_permissions.administrator = False
    member.roles = []

    interaction = MagicMock(guild=guild, user=MagicMock(id=9999))
    assert await is_admin_or_mod(interaction) is False


@pytest.mark.utils
@pytest.mark.access
@pytest.mark.asyncio
async def test_is_admin_or_mod_true_if_admin(guild_with_member):
    """User with admin permissions should return True."""
    guild, member = guild_with_member
    member.guild_permissions.administrator = True
    member.roles = []

    interaction = MagicMock(guild=guild, user=MagicMock(id=1234))
    assert await is_admin_or_mod(interaction) is True


@pytest.mark.utils
@pytest.mark.access
@pytest.mark.asyncio
async def test_is_admin_or_mod_true_if_mod_role_matches(guild_with_member):
    """User with one of the MOD_ROLE_IDS roles should return True."""
    guild, member = guild_with_member
    member.guild_permissions.administrator = False

    mock_mod_role = MagicMock()
    mock_mod_role.id = MOD_ROLE_IDS[0] if MOD_ROLE_IDS else 123456789
    member.roles = [mock_mod_role]

    interaction = MagicMock(guild=guild, user=MagicMock(id=1234))

    with patch("bot.utils.MOD_ROLE_IDS", [mock_mod_role.id]):
        assert await is_admin_or_mod(interaction) is True