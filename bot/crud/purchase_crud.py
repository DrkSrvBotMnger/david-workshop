from sqlalchemy.exc import IntegrityError
from db.schema import RewardEvent, Reward, Inventory, User, Event, EventStatus

class PurchaseError(Exception): ...

def fetch_reward_event(session, reward_event_key: str):
    re = (
        session.query(RewardEvent, Reward, Event)
        .join(Reward, Reward.id == RewardEvent.reward_id)
        .join(Event, Event.id == RewardEvent.event_id)
        .filter(RewardEvent.reward_event_key == reward_event_key)
        .first()
    )
    if not re:
        raise PurchaseError("Unknown shop item.")
    reward_event, reward, event = re
    if reward_event.availability != "inshop":
        raise PurchaseError("This item is not sold in the shop.")
    if event.event_status != EventStatus.active:
        raise PurchaseError("This event is not active.")
    if reward.reward_type == "preset" and not (reward.preset_by and reward.preset_at):
        raise PurchaseError("This preset hasn't been published yet.")
    return reward_event, reward, event

def already_owned_nonstackable(session, user_id: int, reward_id: int, is_stackable: bool) -> bool:
    if is_stackable:
        return False
    inv = session.query(Inventory).filter_by(user_id=user_id, reward_id=reward_id).first()
    return bool(inv)

def apply_purchase(session, user: User, reward_event: RewardEvent, reward: Reward):
    price = reward_event.price or 0
    if user.points < price:
        raise PurchaseError("Not enough points.")

    if already_owned_nonstackable(session, user.id, reward.id, reward.is_stackable):
        raise PurchaseError("You already own this (not stackable).")

    # points
    user.points -= price
    user.total_spent += price
    
    # inventory
    inv = session.query(Inventory).filter_by(user_id=user.id, reward_id=reward.id).first()
    if inv:
        inv.quantity += 1
    else:
        inv = Inventory(user_id=user.id, reward_id=reward.id, quantity=1)
        session.add(inv)
        
    # stats
    reward.number_granted += 1
    
    # Let caller commit
    return inv, price
