from sqlalchemy import case, and_
from typing import Optional, List
from db.schema import Inventory, Reward

def _reward_type_order():
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
      "inv_id": int, "is_equipped": bool,
      "reward_id": int, "reward_key": str, "reward_type": str,
      "reward_name": str, "reward_description": str | None, "emoji": str | None,
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
        )
        .join(Reward, Reward.id == Inventory.reward_id)
        .filter(Inventory.user_id == user_id)
        .order_by(_reward_type_order(), Reward.reward_name.asc())
        .all()
    )
    return [dict(r._asdict()) for r in rows]

def get_equipped_title_name(session, user_id: int) -> Optional[str]:
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