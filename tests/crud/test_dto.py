import pytest
import sqlalchemy.exc
from bot.domain.mapping import to_action_event_dto

def test_to_action_event_dto_handles_help_json_and_fields(
    test_session, base_action, base_action_event, base_reward_event
):
    # Use instance fixtures directly
    action = base_action
    action.input_fields_json = '["url","numeric_value"]'
    action.is_active = True
    action.deactivated_at = None

    revent = base_reward_event  # <-- RewardEvent, not Reward

    ae = base_action_event
    ae.action = action
    ae.reward_event_id = revent.id
    ae.is_numeric_multiplier = True
    ae.input_help_json = '["general tip","url tip"]'
    ae.points_granted = 10
    ae.variant = "default"

    test_session.flush()

    dto = to_action_event_dto(ae, action, revent)

    assert dto.input_fields == ["url", "numeric_value"]
    assert dto.input_help_map["general"] == "general tip"
    assert dto.input_help_map["url"] == "url tip"
    assert "numeric_value" in dto.input_help_map
    assert dto.action_is_active is True
    assert dto.is_numeric_multiplier is True
    assert dto.has_direct_reward is True
    assert dto.points_granted == 10