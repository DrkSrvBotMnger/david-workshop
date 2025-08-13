# bot/services/rewards_service.py
from sqlalchemy.orm import Session
from bot.crud.rewards_crud import get_reward_by_reward_event_id, increment_reward_number_granted
from bot.domain.mapping import reward_to_grant_dto
from bot.domain.dto import RewardGrantDTO

def get_reward_dto_by_reward_event_id(session: Session, reward_event_id: int) -> RewardGrantDTO | None:
    r = get_reward_by_reward_event_id(session, reward_event_id)
    return reward_to_grant_dto(r) if r else None

def bump_reward_granted_counter(session: Session, reward_id: int, qty: int = 1) -> None:
    increment_reward_number_granted(session, reward_id, delta=qty)