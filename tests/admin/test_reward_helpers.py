import pytest
from bot.commands.admin.rewards_admin import AdminRewardCommands


@pytest.mark.admin
@pytest.mark.reward
def test_ensure_reward_prefix_adds_correct_prefix():
    cog = AdminRewardCommands(bot=None)

    # Should add prefix for matching type
    assert cog.ensure_reward_prefix("mytitle", "title") == "t_mytitle"
    assert cog.ensure_reward_prefix("badge123", "badge") == "b_badge123"
    assert cog.ensure_reward_prefix("mypreset", "preset") == "p_mypreset"
    assert cog.ensure_reward_prefix("mydynamic", "dynamic") == "d_mydynamic"


@pytest.mark.admin
@pytest.mark.reward
def test_ensure_reward_prefix_does_not_double_prefix():
    cog = AdminRewardCommands(bot=None)

    # Should leave existing correct prefix untouched
    assert cog.ensure_reward_prefix("t_existing", "title") == "t_existing"
    assert cog.ensure_reward_prefix("b_existing", "badge") == "b_existing"


@pytest.mark.admin
@pytest.mark.reward
def test_is_valid_emoji_returns_true_for_valid_unicode():
    cog = AdminRewardCommands(bot=None)
    assert cog.is_valid_emoji("😀") is True  # Standard unicode emoji


@pytest.mark.admin
@pytest.mark.reward
def test_is_valid_emoji_returns_true_for_valid_custom():
    cog = AdminRewardCommands(bot=None)
    # Custom emoji format <:name:id>
    assert cog.is_valid_emoji("<:custom:123456789012345678>") is True


@pytest.mark.admin
@pytest.mark.reward
def test_is_valid_emoji_returns_false_for_invalid_or_none():
    cog = AdminRewardCommands(bot=None)
    assert cog.is_valid_emoji("") is False
    assert cog.is_valid_emoji(None) is False
    assert cog.is_valid_emoji("not-an-emoji") is False
