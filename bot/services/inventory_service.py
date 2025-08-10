from typing import Dict, Tuple, List
from bot.config.constants import PUBLISHABLE_REWARD_TYPES
from bot.crud.inventory_crud import fetch_user_inventory_ordered

def get_user_publishables_for_preview(session, user_id: int) -> Dict[str, Tuple[str, str, str]]:
    """
    Returns a mapping for the UI select:
      value -> (channel_id, message_id, label)
    where `value` is reward_key (stable), label is reward_name.
    Only includes rows where type is publishable AND both pointers exist.
    """
    items = fetch_user_inventory_ordered(session, user_id)
    out: Dict[str, Tuple[str, str, str]] = {}
    for r in items:
        if r["reward_type"] not in PUBLISHABLE_REWARD_TYPES:
            continue
        ch = r.get("use_channel_discord_id")
        msg = r.get("use_message_discord_id")
        if not (ch and msg):
            continue
        value = str(r["reward_key"])
        out[value] = (str(ch), str(msg), str(r["reward_name"] or value))
    return out
