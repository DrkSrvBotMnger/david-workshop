import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.utils import is_admin_or_mod

@pytest.fixture
def mock_interaction():
    mock = MagicMock()
    mock.user.id = 1234
    mock.user.mention = "<@1234>"
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    mock.guild.get_channel = MagicMock(return_value=AsyncMock(send=AsyncMock()))
    return mock


@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_is_admin_or_mod_false_for_regular_user():
    mock_member = MagicMock()
    mock_member.guild_permissions.administrator = False
    mock_member.roles = []  # No roles

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)

    mock_interaction = MagicMock()
    mock_interaction.user.id = 9999
    mock_interaction.guild = mock_guild

    result = await is_admin_or_mod(mock_interaction)
    assert result is False


@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_is_admin_or_mod_true_if_admin():
    mock_member = MagicMock()
    mock_member.guild_permissions.administrator = True
    mock_member.roles = []

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)

    mock_interaction = MagicMock()
    mock_interaction.user.id = 1234
    mock_interaction.guild = mock_guild

    result = await is_admin_or_mod(mock_interaction)
    assert result is True


@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_is_admin_or_mod_true_if_mod_role_matches():
    from bot import utils
    mock_member = MagicMock()
    mock_member.guild_permissions.administrator = False

    mock_mod_role = MagicMock()
    mock_mod_role.id = utils.MOD_ROLE_IDS[0] if utils.MOD_ROLE_IDS else 123456789
    mock_member.roles = [mock_mod_role]

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)

    mock_interaction = MagicMock()
    mock_interaction.user.id = 1234
    mock_interaction.guild = mock_guild

    with patch("bot.utils.MOD_ROLE_IDS", [mock_mod_role.id]):
        result = await is_admin_or_mod(mock_interaction)
        assert result is True