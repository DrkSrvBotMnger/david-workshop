# bot/config/constants.py
import regex

# Allowed input fields for Action definitions
ALLOWED_ACTION_INPUT_FIELDS = [
    "url_value", "numeric_value", "text_value", "boolean_value", "date_value"
]
SUPPORTED_FIELDS = set(ALLOWED_ACTION_INPUT_FIELDS)

EVENT_TYPES = ("freeform", "prompt")

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

TRIGGER_TYPES = [
    ("prompt_count", "prompt", "Count prompts", "Submit X prompts in one report"),
    ("prompt_unique", "prompt", "Number of unique prompt", "Complete X different prompts in total"),
    ("prompt_repeat", "prompt", "Repeat prompt", "Do Y prompt X times"),
    ("streak", "all", "Streak trigger", "Participate X days in a row"),
    ("event_count", "all", "Count actions", "Submit X actions/reports"),
    ("action_repeat", "all", "Repeat action", "Do Y action X times"),
    ("points_won", "all", "Number of points won", "Earn X points in the event"),
    ("participation_days", "all", "Number of participation days", "Participate on X unique days"),
    ("global_count", "global", "Global - count actions", "Submit X actions/reports globally"),
    ("global_points_won", "global", "Global - number of points won", "Earn X points globally"),
]