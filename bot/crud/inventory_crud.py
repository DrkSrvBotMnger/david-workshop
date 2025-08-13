# bot/crud/inventory_crud.py
from sqlalchemy.orm import Session
from sqlalchemy import case, and_, func
from typing import Optional, List, Iterable

from db.schema import Inventory, Reward

def reward_type_order():
    """Order rewards by type: title, badge, preset, other."""
    return case(
        (Reward.reward_type == "title", 0),
        (Reward.reward_type == "badge", 1),
        (Reward.reward_type == "preset", 2),
        else_=3
    )

def fetch_user_inventory_ordered(session, user_id: int) -> list[dict]:
    """
    Returns rows shaped for UI:
    {
      "inv_id": int, 
      "is_equipped": bool,
      "reward_id": int, 
      "reward_key": str, 
      "reward_type": str,
      "reward_name": str, 
      "reward_description": str | None, 
      "emoji": str | None,
      "preset_channel_discord_id": str | None,
      "preset_message_discord_id": str | None,
    }
    """
    rows = (
        session.query(
            Inventory.id.label("inv_id"),
            Inventory.is_equipped,
            Reward.id.label("reward_id"),
            Reward.reward_key,
            Reward.reward_type,
            Reward.reward_name,
            Reward.reward_description,
            Reward.emoji,
            Reward.use_channel_discord_id,
            Reward.use_message_discord_id,
        )
        .join(Reward, Reward.id == Inventory.reward_id)
        .filter(Inventory.user_id == user_id)
        .order_by(reward_type_order(), Reward.reward_name.asc())
        .all()
    )
    return [dict(r._asdict()) for r in rows]

def get_equipped_title_name(session, user_id: int) -> Optional[str]:
    """Returns the name of the equipped title, or None if no title is equipped."""
    row = (
        session.query(Reward.reward_name)
        .join(Inventory, Inventory.reward_id == Reward.id)
        .filter(
            and_(
                Inventory.user_id == user_id,
                Inventory.is_equipped.is_(True),
                Reward.reward_type == "title",
            )
        )
        .first()
    )
    return row[0] if row else None

def get_equipped_badge_emojis(session, user_id: int) -> List[str]:
    """Returns a list of emojis for equipped badges, or an empty list if no badges are equipped."""
    rows = (
        session.query(Reward.emoji)
        .join(Inventory, Inventory.reward_id == Reward.id)
        .filter(
            and_(
                Inventory.user_id == user_id,
                Inventory.is_equipped.is_(True),
                Reward.reward_type == "badge",
            )
        )
        .all()
    )
    # keep only non-empty
    return [str(emoji) for (emoji,) in rows if emoji]

def fetch_user_titles_for_equip(session, user_id: int):
    """Returns [(reward_key, reward_name, is_equipped)]"""
    rows = (
        session.query(Reward.reward_key, Reward.reward_name, Inventory.is_equipped)
        .join(Inventory, Inventory.reward_id == Reward.id)
        .filter(Inventory.user_id == user_id, Reward.reward_type == "title")
        .order_by(func.lower(Reward.reward_name).asc())
        .all()
    )
    return rows

def fetch_user_badges_for_equip(session, user_id: int):
    """Returns [(reward_key, reward_name, emoji, is_equipped)]"""
    rows = (
        session.query(Reward.reward_key, Reward.reward_name, Reward.emoji, Inventory.is_equipped)
        .join(Inventory, Inventory.reward_id == Reward.id)
        .filter(Inventory.user_id == user_id, Reward.reward_type == "badge")
        .order_by(func.lower(Reward.reward_name).asc())
        .all()
    )
    return rows

def set_titles_equipped(session: Session, user_id: int, selected_key: Optional[str]) -> int:
    """
    Equip exactly one title for user (or none if selected_key is None).
    Returns number of rows updated.
    """
    items = (
        session.query(Inventory).join(Reward, Reward.id == Inventory.reward_id)
        .filter(Inventory.user_id == user_id, Reward.reward_type == "title")
        .all()
    )
    updated = 0
    for it in items:
        new_val = (it.reward.reward_key == selected_key) if selected_key else False
        if it.is_equipped != new_val:
            it.is_equipped = new_val
            updated += 1
    session.flush()
    return updated

def set_badges_equipped(session: Session, user_id: int, selected_keys: Iterable[str]) -> int:
    """
    Equip badges by reward_key (multiple). Non-selected become unequipped.
    Returns number of rows updated.
    """
    selected = set(selected_keys)
    items = (
        session.query(Inventory).join(Reward, Reward.id == Inventory.reward_id)
        .filter(Inventory.user_id == user_id, Reward.reward_type == "badge")
        .all()
    )
    updated = 0
    for it in items:
        new_val = it.reward.reward_key in selected
        if it.is_equipped != new_val:
            it.is_equipped = new_val
            updated += 1
    session.flush()
    return updated

def add_or_increment_inventory(
    session: Session, *, user_id: int, reward_id: int, is_stackable: bool
) -> None:
    inv = (
        session.query(Inventory)
        .filter(Inventory.user_id == user_id, Inventory.reward_id == reward_id)
        .first()
    )
    if inv:
        if is_stackable:
            inv.quantity = (inv.quantity or 0) + 1
    else:
        session.add(Inventory(user_id=user_id, reward_id=reward_id, quantity=1))
    session.flush()
