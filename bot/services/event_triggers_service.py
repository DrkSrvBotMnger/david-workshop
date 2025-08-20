# bot/services/event_triggers_service.py
from __future__ import annotations

import json
from typing import Iterable, Optional, Tuple, Dict, Any, Set, List, Callable 
from sqlalchemy import func

from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime, date, timedelta
from db.database import db_session
from bot.crud.event_triggers_crud import (
    create_event_trigger,
    get_event_triggers_for_event,
    get_global_event_triggers,
    get_event_trigger_by_id,
    check_event_trigger_exists,
    update_event_trigger,
    delete_event_trigger,
    log_event_trigger_grant,
    has_user_event_trigger_log,
)
from bot.crud.events_crud import get_event_by_id
from bot.crud.users_crud import get_or_create_user
from bot.domain.mapping import (
    to_event_trigger_dto,
    to_user_event_trigger_log_dto,
)
from db.schema import (
    Event, EventTrigger, RewardEvent, Reward, Inventory, UserAction,
    UserEventData, User, EventPrompt, UserActionPrompt  # add EventPrompt, UserActionPrompt
)
from bot.services.users_service import get_or_create_user_dto
from bot.services.events_service import get_event_dto_by_id

from bot.utils.formatting import now_iso
from bot.utils.discord_helpers import format_trigger_label
from bot.config import CURRENCY

def apply_triggers_after_action_id(
    user_action_id: int,
    current_prompt_ids: Optional[Iterable[int]] = None
) -> List[str]:
    """
    Convenience wrapper:
    Load (user, event, action) by user_action_id, then evaluate and apply triggers.
    Returns formatted grant lines ready to display to the user.
    """
    with db_session() as session:
        ua = session.query(UserAction).get(user_action_id)
        if not ua:
            return []
        user = session.query(User).get(ua.user_id)
        event = session.query(Event).get(ua.event_id)
        if not user or not event:
            return []

        lines = check_and_apply_triggers_for_action(
            session,
            user=user,
            event=event,
            current_action=ua,
            current_prompts=current_prompt_ids
        )
        session.commit()
        return lines


def create_event_trigger_service(create_data: dict):
    with db_session() as session:
        existing = check_event_trigger_exists(session, create_data["event_id"], create_data["trigger_type"], create_data["config"])
        if existing:
            raise ValueError("⚠️ A trigger with the same type and config already exists for this event.")
        trigger = create_event_trigger(session, create_data)
        return to_event_trigger_dto(trigger)

def update_event_trigger_service(trigger_id: int, update_data: dict):
    with db_session() as session:
        trigger = update_event_trigger(session, trigger_id, update_data)
        return to_event_trigger_dto(trigger) if trigger else None

def delete_event_trigger_service(trigger_id: int) -> bool:
    with db_session() as session:
        return delete_event_trigger(session, trigger_id)

def get_event_triggers_service(event_id: int) -> list:
    with db_session() as session:
        triggers = get_event_triggers_for_event(session, event_id)
        return [to_event_trigger_dto(t) for t in triggers]

def get_global_event_triggers_service() -> list:
    with db_session() as session:
        triggers = get_global_event_triggers(session)
        return [to_event_trigger_dto(t) for t in triggers]

def get_event_trigger_service(trigger_id: int):
    with db_session() as session:
        trigger = get_event_trigger_by_id(session, trigger_id)
        return to_event_trigger_dto(trigger) if trigger else None

def log_user_event_trigger_service(user_id: int, trigger_id: int):
    with db_session() as session:
        log = log_event_trigger_grant(session, user_id, trigger_id)
        return to_user_event_trigger_log_dto(log)

def has_user_event_trigger_service(user_id: int, trigger_id: int) -> bool:
    with db_session() as session:
        return has_user_event_trigger_log(session, user_id, trigger_id)






def get_reward_event_by_key(session, event_id: int, reward_event_key: str):
    return (
        session.query(RewardEvent)  # type: ignore
        .filter_by(event_id=event_id, reward_event_key=reward_event_key)
        .first()
    )

def _parse_config(config_json: Optional[str]) -> Dict[str, Any]:
    if not config_json:
        return {}
    try:
        return json.loads(config_json)
    except Exception:
        return {}

def _ensure_exactly_one(reward_event_key: Optional[str], points: Optional[int]) -> None:
    provided = sum([1 if (reward_event_key and reward_event_key.strip()) else 0, 1 if points is not None else 0])
    if provided != 1:
        raise ValueError("You must provide exactly one of reward_event_key or points.")

def _validate_points(points: Optional[int]) -> int:
    if points is None:
        raise ValueError("Points value is missing.")
    if not isinstance(points, int) or points <= 0:
        raise ValueError("Points must be a positive integer.")
    return points

def link_grant_to_trigger(
    *,
    event_id: int,
    trigger_id: int,
    reward_event_key: Optional[str],
    points: Optional[int],
    actor_discord_id: int,
) -> Dict[str, Any]:
    """
    Attach a grant (reward or points) to an EventTrigger.
    - If reward_event_key is provided -> sets reward_event_id and clears points_granted
    - If points is provided -> sets points_granted and clears reward_event_id

    Returns a summary dict for UI.
    Raises ValueError for user-facing validation errors.
    """
    _ensure_exactly_one(reward_event_key, points)

    with db_session() as session:
        # 1) Validate event & trigger
        ev = get_event_by_id(session, event_id)
        if not ev:
            raise ValueError(f"Event `{event_id}` was not found.")

        trigger = get_event_trigger_by_id(session, trigger_id)
        if not trigger:
            raise ValueError(f"Trigger `{trigger_id}` was not found.")
        if getattr(trigger, "event_id", None) != event_id:
            raise ValueError(
                f"Trigger `{trigger_id}` does not belong to event `{event_id}` "
                f"(belongs to event `{getattr(trigger, 'event_id', None)}`)."
            )

        warnings: list[str] = []
        update_data: Dict[str, Any] = {}
        config = _parse_config(getattr(trigger, "config_json", None))

        # 2) Mode: Reward
        if reward_event_key and reward_event_key.strip():
            rk = reward_event_key.strip()

            revent = get_reward_event_by_key(session, event_id, rk)
            if not revent:
                raise ValueError(f"Reward with key `{rk}` was not found in event `{event_id}`.")

            # Gentle warning if we’re overwriting a previous choice
            prev_points = getattr(trigger, "points_granted", None)
            prev_reward = getattr(trigger, "reward_event_id", None)
            if prev_points:
                warnings.append("Overwriting an existing points grant on this trigger.")
            if prev_reward and prev_reward != getattr(revent, "id", None):
                warnings.append("Replacing a different reward that was already linked to this trigger.")

            update_data["reward_event_id"] = revent.id
            update_data["points_granted"] = None

            # Optional: warn if the reward is already accessible elsewhere (shop, on-action, etc.)
            # This assumes RewardEvent has an 'availability' or flags; adapt to your schema.
            try:
                availability = getattr(revent, "availability", None) or getattr(revent, "available_in", None)
                if availability:
                    if "shop" in str(availability):
                        warnings.append("This reward also appears **in shop**.")
                    if "onaction" in str(availability):
                        warnings.append("This reward is also granted **on action**.")
            except Exception:
                # Silent if your schema doesn't support this yet
                pass

            grant_type = "reward"
            grant_points = None
            grant_reward_event_key = rk

        # 3) Mode: Points
        else:
            pts = _validate_points(points)
    
            prev_points = getattr(trigger, "points_granted", None)
            prev_reward = getattr(trigger, "reward_event_id", None)
            if prev_reward:
                warnings.append("Overwriting an existing reward grant on this trigger.")
            if prev_points and prev_points != pts:
                warnings.append(f"Replacing previous points value ({prev_points}) with {pts}.")
    
            update_data["points_granted"] = pts
            update_data["reward_event_id"] = None
    
            grant_type = "points"
            grant_points = pts
            grant_reward_event_key = None
    
        # 4) Persist config + grant
        if config:
            update_data["config"] = config
    
        updated = update_event_trigger(session, trigger_id, update_data)
        if not updated:
            # Extremely unlikely: trigger was deleted between fetch and update
            raise ValueError("Failed to update the trigger; please try again.")
    
        # 5) Build UI summary
        trigger_label = _derive_trigger_label(updated)
        summary: Dict[str, Any] = {
            "event_id": event_id,
            "trigger_id": trigger_id,
            "trigger_label": trigger_label,
            "grant_type": grant_type,            # "reward" | "points"
            "reward_event_key": grant_reward_event_key,      # str | None
            "points": grant_points,              # int | None
            "warnings": warnings,
        }
        return summary
    
def _derive_trigger_label(trigger_obj) -> str:
    """
    Try to produce a friendly label for the trigger to show in admin confirmations.
    Uses config.label if available, otherwise falls back to trigger_type + brief config.
    """
    try:
        cfg = _parse_config(getattr(trigger_obj, "config_json", None))
        if "label" in cfg and str(cfg["label"]).strip():
            return str(cfg["label"]).strip()

        # Compact, human-ish fallback (avoid leaking big configs in UI)
        ttype = getattr(trigger_obj, "trigger_type", "") or "trigger"
        parts: list[str] = [ttype]
        for k in ("X", "Y", "count", "days", "action", "prompt"):
            if k in cfg:
                parts.append(f"{k}={cfg[k]}")
        return " • ".join(parts)
    except Exception:
        return str(getattr(trigger_obj, "trigger_type", "trigger"))





# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_and_apply_triggers_for_action(
    session: Session,
    *,
    user: User,
    event: Event,
    current_action: UserAction,
    current_prompts: Optional[Iterable[int]] = None,
) -> List[str]:
    """
    Evaluate ALL triggers for this event after an action submission.
    Multiple triggers can be granted in the same report.
    Returns a list of fully formatted lines, e.g.:
      ["🎉 Do Y prompt X times: 🏅 badge - Name", "🎉 Submit X prompts in one report: ⭐ 50 vlachki"]
    """
    triggers = get_event_triggers_for_event(session, event.id)
    if not triggers:
        return []

    # ---- Precompute / context shared by all evaluators
    all_actions: List[UserAction] = (
        session.query(UserAction)
        .filter(UserAction.user_id == user.id, UserAction.event_id == event.id)
        .all()
    )
    if current_action not in all_actions:
        all_actions.append(current_action)

    # Current submission prompts
    if current_prompts is None:
        current_prompt_set = _get_prompts_for_action(session, current_action.id)
    else:
        current_prompt_set = {int(p) for p in current_prompts}

    # Historical prompt stats
    distinct_prompt_ids, per_prompt_counts = _aggregate_user_prompts(
        session, [ua.id for ua in all_actions]
    )

    # Participation days set (for streak, participation_days)
    participation_days = _collect_participation_days(all_actions)

    # Event points earned so far (before this trigger pass)
    ued = (
        session.query(UserEventData)
        .filter(UserEventData.user_id == user.id, UserEventData.event_id == event.id)
        .first()
    )
    points_earned_in_event = ued.points_earned if ued else 0

    ctx: Dict[str, Any] = {
        "all_actions": all_actions,
        "current_prompts": current_prompt_set,         # set[int] of EventPrompt IDs
        "distinct_prompts": distinct_prompt_ids,       # set[int]
        "per_prompt_counts": per_prompt_counts,        # {prompt_id: count}
        "participation_days": participation_days,      # set[date]
        "event_points_earned": points_earned_in_event, # int
        "global_points_earned": int(getattr(user, "total_earned", 0)),
    }

    # Evaluators registry
    evaluators: Dict[str, Callable[[Session, User, Event, Dict[str, Any], Dict[str, Any]], Tuple[bool, str]]] = {
        "prompt_count": _eval_prompt_count,
        "prompt_unique": _eval_prompt_unique,
        "prompt_repeat": _eval_prompt_repeat,
        "streak": _eval_streak,
        "event_count": _eval_event_count,
        "action_repeat": _eval_action_repeat,
        "points_won": _eval_points_won,
        "participation_days": _eval_participation_days,
        "global_count": _eval_global_count,
        "global_points_won": _eval_global_points_won,
    }

    grant_lines: List[str] = []

    for trig in triggers:
        # Skip if already granted to this user
        if has_user_event_trigger_log(session, user.id, trig.id):
            continue

        ttype = (getattr(trig, "trigger_type", "") or "").strip()
        cfg = _loads_json(getattr(trig, "config_json", None))

        evaluator = evaluators.get(ttype)
        if not evaluator:
            continue  # unknown/disabled trigger type

        achieved, _detail = evaluator(session, user, event, ctx, cfg)
        if not achieved:
            continue

        grant = _apply_trigger_grant(session, user, event, trig)
        if grant:
            # Human label for the *trigger* (e.g., "Do Y prompt X times", "Submit X prompts in one report", …)
            label = format_trigger_label(ttype, cfg, getattr(event, "id", None))

            if grant.get("kind") == "points":
                line = f"🎉 {label}: ⭐ **{int(grant['points'])}** {CURRENCY}"
            else:
                rtype = str(grant.get("reward_type", "") or "").strip()
                rname = str(grant.get("reward_name", "") or "").strip()
                line = f"🎉 {label}: 🏅 {rtype} - **{rname}**"

            grant_lines.append(line)

        # Log it (unique constraint guarantees idempotency)
        log_event_trigger_grant(session, user.id, trig.id)

        # If evaluator depends on evolving context (e.g., points_won), refresh ctx
        if ttype in ("points_won",):
            ued2 = (
                session.query(UserEventData)
                .filter(UserEventData.user_id == user.id, UserEventData.event_id == event.id)
                .first()
            )
            ctx["event_points_earned"] = ued2.points_earned if ued2 else ctx["event_points_earned"]

        if ttype in ("global_points_won",):
            ctx["global_points_earned"] = int(getattr(user, "total_earned", ctx["global_points_earned"]))

    return grant_lines



# ---------------------------------------------------------------------------
# Evaluators (pure-ish; read-only except via ctx)
# Each returns (achieved: bool, detail: str)
# ---------------------------------------------------------------------------

def _eval_prompt_count(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_count = _as_int(cfg.get("min_count"), default=0)
    cur = len(ctx["current_prompts"])
    ok = cur >= min_count
    return ok, f"({cur}/{min_count} prompts in one report)" if ok else ""

def _normalize_group_str(cfg: Dict[str, Any]) -> Optional[str]:
    """
    Returns a normalized group string, or None when config means 'all groups'.
    Accepts: None, "", "all", "*" -> None
             otherwise: trimmed string (case preserved for messaging)
    """
    v = cfg.get("group", None)
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in ("all", "*"):
        return None
    return s

def _eval_prompt_unique(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Achieved if the user has completed at least `min_count` different prompts.
    If `group` is provided (string), only count unique prompts within that group.
      cfg = { "min_count": int, "group": str | "all" | "" | "*" (optional) }

    Uses ctx["distinct_prompts"] which is the set of EventPrompt IDs
    across the user's actions for this event.
    """
    min_count = _as_int(cfg.get("min_count"), default=0)
    if min_count <= 0:
        return False, ""

    distinct_ids: Set[int] = ctx.get("distinct_prompts", set()) or set()
    if not distinct_ids:
        return False, ""

    group_str = _normalize_group_str(cfg)

    # All groups
    if group_str is None:
        uniq = len(distinct_ids)
        ok = uniq >= min_count
        return ok, f"({uniq}/{min_count} unique prompts)"

    # Group-aware: EventPrompt.group is a STRING; match case-insensitively
    rows = (
        session.query(EventPrompt.id)
        .filter(
            EventPrompt.event_id == event.id,
            EventPrompt.id.in_(list(distinct_ids)),
            func.lower(EventPrompt.group) == group_str.lower(),
        )
        .all()
    )
    uniq = len(rows)
    ok = uniq >= min_count
    return ok, f"({uniq}/{min_count} unique prompts in group {group_str})"

def _eval_prompt_repeat(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    prompt_code = str(cfg.get("prompt_code") or "").strip()
    min_count = _as_int(cfg.get("min_count"), default=0)
    if not prompt_code or min_count <= 0:
        return False, ""

    ep = (
        session.query(EventPrompt)
        .filter_by(event_id=event.id, code=prompt_code)
        .first()
    )
    if not ep:
        return False, ""

    count_for_prompt = ctx["per_prompt_counts"].get(ep.id, 0)
    ok = count_for_prompt >= min_count
    return ok, f"(prompt {prompt_code} {count_for_prompt}/{min_count} times)" if ok else ""

def _eval_streak(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_days = _as_int(cfg.get("min_days"), default=0)
    if min_days <= 0 or not ctx["participation_days"]:
        return False, ""
    streak_len = _ending_streak_length(ctx["participation_days"])
    ok = streak_len >= min_days
    return ok, f"({streak_len}/{min_days} days in a row)" if ok else ""

def _eval_event_count(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_reports = _as_int(cfg.get("min_reports"), default=0)
    total = len(ctx["all_actions"])
    ok = total >= min_reports
    return ok, f"({total}/{min_reports} reports)" if ok else ""

def _eval_action_repeat(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    ae_id = _as_int(cfg.get("action_event_id"), default=0)
    min_count = _as_int(cfg.get("min_count"), default=0)
    if ae_id <= 0 or min_count <= 0:
        return False, ""
    count = sum(1 for ua in ctx["all_actions"] if int(getattr(ua, "action_event_id", 0)) == ae_id)
    ok = count >= min_count
    return ok, f"(action {ae_id} {count}/{min_count} times)" if ok else ""

def _eval_points_won(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_points = _as_int(cfg.get("min_points"), default=0)
    earned = int(ctx["event_points_earned"])
    ok = earned >= min_points
    return ok, f"({earned}/{min_points} points)" if ok else ""

def _eval_participation_days(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_days = _as_int(cfg.get("min_days"), default=0)
    days = len(ctx["participation_days"])
    ok = days >= min_days
    return ok, f"({days}/{min_days} days)" if ok else ""

def _eval_global_count(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_reports = _as_int(cfg.get("min_reports"), default=0)
    total = session.query(UserAction).filter(UserAction.user_id == user.id).count()
    ok = total >= min_reports
    return ok, f"({total}/{min_reports} reports global)" if ok else ""

def _eval_global_points_won(session: Session, user: User, event: Event, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[bool, str]:
    min_points = _as_int(cfg.get("min_points"), default=0)
    total_points = int(ctx["global_points_earned"])
    ok = total_points >= min_points
    return ok, f"({total_points}/{min_points} global points)" if ok else ""


# ---------------------------------------------------------------------------
# Grant application
# ---------------------------------------------------------------------------

def _apply_trigger_grant(session: Session, user: User, event: Event, trig) -> Optional[Dict[str, Any]]:
    """
    Apply either points or reward from the EventTrigger.
    Updates User, UserEventData, Inventory as needed.
    Returns a dict describing the grant for downstream formatting:
      - {"kind": "points", "points": int}
      - {"kind": "reward", "reward_type": str, "reward_name": str}
    """
    points = getattr(trig, "points_granted", None)
    reward_event_id = getattr(trig, "reward_event_id", None)

    # Points path
    if isinstance(points, int) and points > 0:
        user.points += points
        user.total_earned += points

        ued = (
            session.query(UserEventData)
            .filter(UserEventData.user_id == user.id, UserEventData.event_id == event.id)
            .first()
        )
        if not ued:
            ued = UserEventData(
                user_id=user.id,
                event_id=event.id,
                points_earned=0,
                joined_at=now_iso(),
                created_by=str(user.user_discord_id) if hasattr(user, "user_discord_id") else "system",
            )
            session.add(ued)
        ued.points_earned += points
        return {"kind": "points", "points": int(points)}

    # Reward path
    if reward_event_id:
        revent: RewardEvent | None = session.query(RewardEvent).get(reward_event_id)
        if not revent:
            return None
        reward: Reward | None = session.query(Reward).get(revent.reward_id)
        if not reward:
            return None

        inv = (
            session.query(Inventory)
            .filter(Inventory.user_id == user.id, Inventory.reward_id == reward.id)
            .first()
        )
        if inv:
            if getattr(reward, "is_stackable", False):
                inv.quantity += 1
        else:
            inv = Inventory(user_id=user.id, reward_id=reward.id, quantity=1)
            session.add(inv)

        reward.number_granted += 1
        return {"kind": "reward", "reward_type": str(reward.reward_type), "reward_name": str(reward.reward_name)}

    return None


# ---------------------------------------------------------------------------
# Prompt aggregation helpers (DB-backed)
# ---------------------------------------------------------------------------

def _get_prompts_for_action(session: Session, user_action_id: int) -> Set[int]:
    rows = (
        session.query(UserActionPrompt.event_prompt_id)
        .filter(UserActionPrompt.user_action_id == user_action_id)
        .all()
    )
    return {int(r[0]) for r in rows}

def _aggregate_user_prompts(session: Session, user_action_ids: List[int]) -> Tuple[Set[int], Dict[int, int]]:
    distinct: Set[int] = set()
    counts: Dict[int, int] = {}
    if not user_action_ids:
        return distinct, counts

    rows = (
        session.query(UserActionPrompt.event_prompt_id)
        .filter(UserActionPrompt.user_action_id.in_(user_action_ids))
        .all()
    )
    for (pid,) in rows:
        pid = int(pid)
        distinct.add(pid)
        counts[pid] = counts.get(pid, 0) + 1
    return distinct, counts


# ---------------------------------------------------------------------------
# Date / streak helpers
# ---------------------------------------------------------------------------

def _parse_iso_date(s: str) -> Optional[date]:
    try:
        # Accept "YYYY-MM-DD" or full ISO "YYYY-MM-DDTHH:MM:SS[±HH:MM]"
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return date.fromisoformat(s)
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _collect_participation_days(actions: Iterable[UserAction]) -> Set[date]:
    """
    Streaks are based ONLY on civil days derived from `created_at`.
    We *do not* look at `date_value` here.
    """
    days: Set[date] = set()
    for ua in actions:
        ca = getattr(ua, "created_at", None)
        if not ca:
            continue
        d = _parse_iso_date(str(ca))
        if d:
            days.add(d)
    return days

def _ending_streak_length(days: Set[date]) -> int:
    if not days:
        return 0
    last = max(days)
    length = 1
    cur = last
    while True:
        prev = cur - timedelta(days=1)
        if prev in days:
            length += 1
            cur = prev
        else:
            break
    return length


# ---------------------------------------------------------------------------
# Small utils
# ---------------------------------------------------------------------------

def _loads_json(s: Optional[str]) -> Dict[str, Any]:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}

def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default
