# bot/presentation/actions_presentation.py
from bot.domain.dto import ActionEventDTO

CURRENCY = ":coin:"

def format_action_option_label(dto: ActionEventDTO) -> str:
    base = f"{dto.action_description}"
    if dto.variant and dto.variant.lower() != "default":
        base += f" ({dto.variant})"
    # Points vs direct reward
    right = f" – {dto.points_granted} {CURRENCY}" if dto.points_granted else ""
    if dto.has_direct_reward:
        right = " – 🏆"
    return base + right

def format_action_option_desc(dto: ActionEventDTO) -> str:
    # Use general help if present
    general = dto.input_help_map.get("general", "") if dto.input_help_map else ""
    return general[:100]  # discord select desc is short; trim to taste