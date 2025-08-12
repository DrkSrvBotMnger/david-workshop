# bot/config/constants.py
import regex

# Allowed input fields for Action definitions
ALLOWED_ACTION_INPUT_FIELDS = [
    "url", "numeric_value", "text_value", "boolean_value", "date_value"
]
SUPPORTED_FIELDS = set(ALLOWED_ACTION_INPUT_FIELDS)

# Pagination settings
ACTIONS_PER_PAGE = 5
EVENTS_PER_PAGE  = 5
REWARDS_PER_PAGE = 5
LOGS_PER_PAGE    = 5

# Reward-type groupings / rules
EMOJI_TYPES = ("badge",)
STACKABLE_TYPES = ("preset", "dynamic")
PUBLISHABLE_REWARD_TYPES = ("preset", "dynamic")

EXCLUDED_LOG_FIELDS = {"created_by", "created_at", "modified_by", "modified_at", "preset_by", "preset_at"}

# ✅ Custom Discord emoji: <:name:id> or <a:name:id>
CUSTOM_DISCORD_EMOJI = regex.compile(r"^<a?:[A-Za-z0-9_]{2,32}:\d{17,20}>$")

# ✅ Unicode emoji (single grapheme, supports ZWJ sequences + optional VS)
UNICODE_EMOJI = regex.compile(
    r"^(?:\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?"
    r"(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*"
    r"|\d\uFE0F\u20E3|[#*]\uFE0F\u20E3)$",
    flags=regex.VERSION1,
)

 # display limit on profile
MAX_BADGES = 12 

# bot currency
CURRENCY = "vlachki"