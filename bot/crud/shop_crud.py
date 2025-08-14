from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload
from db.schema import Event, RewardEvent, Reward, EventStatus

def is_preset_published_clause(Reward):
    return and_(Reward.preset_by.isnot(None), Reward.preset_at.isnot(None))

def get_inshop_catalog_grouped(session):
    # Query only once, grab all fields you need
    rows = (
        session.query(
            Event.id,
            Event.event_name,
            RewardEvent.reward_event_key,
            RewardEvent.price,
            Reward.reward_name,
            Reward.reward_type,
            Reward.reward_description,
            Reward.emoji,
        )
        .join(RewardEvent, RewardEvent.event_id == Event.id)
        .join(Reward, RewardEvent.reward_id == Reward.id)
        .filter(
            Event.event_status == EventStatus.active,
            RewardEvent.availability == "inshop",
            or_(Reward.reward_type != "preset", is_preset_published_clause(Reward)),
        )
        .order_by(Event.priority.desc(), Reward.reward_name.asc())
        .all()
    )

    # Group into primitives (no ORM objects)
    pages_by_event = {}
    for ev_id, ev_name, re_key, re_price, rw_name, rw_type, re_desc, re_emoji in rows:
        if ev_id not in pages_by_event:
            pages_by_event[ev_id] = {
                "event_id": ev_id,
                "event_name": ev_name,
                "items": []
            }
        pages_by_event[ev_id]["items"].append({
            "reward_event_key": re_key,
            "price": re_price,
            "reward_name": rw_name,
            "reward_type": rw_type,
            "reward_description": re_desc,
            "emoji":re_emoji,
        })

    # Return a list of event pages
    return list(pages_by_event.values())