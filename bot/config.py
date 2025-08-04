import os
import re

ENV = os.getenv("ENV", "dev").lower()

# Development config (Replit)
DEV_CONFIG = {
    "MOD_ROLE_IDS": [
        1386917677389582427, 849835131182383145, 930538612754382869, 942193816880963694, 1393027937569341522
    ],
    "EMBED_CHANNEL_ID": 1398364541707882637,  # Dev embed archive channel
    "EVENT_ANNOUNCEMENT_CHANNEL_ID": 1135642815687303260, # Dev bot annoucement channel
    "TICKET_CHANNEL_ID" : 1231672338010083430,
    "REWARD_PRESET_CHANNEL_ID": 1400290947861839912,
    "REWARD_PRESET_ARCHIVE_CHANNEL_ID": 1400290999351377980
}

# Production config (Railway)
PROD_CONFIG = {
    "MOD_ROLE_IDS": [
        849835131182383145, 930538612754382869, 942193816880963694
    ],
    "EMBED_CHANNEL_ID": 1398155225788977255,  # Prod embed archive channel
    "EVENT_ANNOUNCEMENT_CHANNEL_ID": 1135642815687303260, # Prod bot annoucement channel
    "TICKET_CHANNEL_ID" : 891142997218037870,
    "REWARD_PRESET_CHANNEL_ID": 1135642815687303260,
    "REWARD_PRESET_ARCHIVE_CHANNEL_ID": 1135642815687303260
}

CONFIG = DEV_CONFIG if ENV == "dev" else PROD_CONFIG

# Easy access in other files:
MOD_ROLE_IDS = CONFIG["MOD_ROLE_IDS"]
EMBED_CHANNEL_ID = CONFIG["EMBED_CHANNEL_ID"]
EVENT_ANNOUNCEMENT_CHANNEL_ID = CONFIG["EVENT_ANNOUNCEMENT_CHANNEL_ID"]
TICKET_CHANNEL_ID = CONFIG["TICKET_CHANNEL_ID"]
REWARD_PRESET_CHANNEL_ID = CONFIG["REWARD_PRESET_CHANNEL_ID"]
REWARD_PRESET_ARCHIVE_CHANNEL_ID = CONFIG["REWARD_PRESET_ARCHIVE_CHANNEL_ID"]

# Allowed input fields for Action definitions
ALLOWED_ACTION_INPUT_FIELDS = [
    "url",
    "numeric_value",
    "text_value",
    "boolean_value",
    "date_value"
]

# Pagination settings
ACTIONS_PER_PAGE = 5           # Admin action listing
EVENTS_PER_PAGE = 5            # Event listing
REWARDS_PER_PAGE = 5           # Shop reward listing
LOGS_PER_PAGE = 5              # Event/user logs

# Matches standard Unicode emoji OR Discord custom emoji format
EMOJI_REGEX = re.compile(
    r"^<a?:\w+:\d+>$"  # Discord custom emoji
    r"|"
    r"^[\U0001F300-\U0001FAD6\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]$"  # Unicode emoji
)

# Reward types to set mandatory fields
BADGE_TYPES = ("badge",)
STACKABLE_TYPES = ("preset", "dynamic",)
PUBLISHABLE_REWARD_TYPES = ("preset", "dynamic",)

EXCLUDED_LOG_FIELDS = {"created_by", "created_at", "modified_by", "modified_at", "preset_by", "preset_at"}
