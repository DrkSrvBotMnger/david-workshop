import os
import re
import regex


ENV = os.getenv("ENV", "dev").lower()

# Development config / Test unitaire config (Replit) 
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

# QA config (Railway)
QA_CONFIG = {
    "MOD_ROLE_IDS": [
        1392541137415311410
    ],
    "EMBED_CHANNEL_ID": 1403469932955697202,
    "EVENT_ANNOUNCEMENT_CHANNEL_ID": 1403469849690116137,
    "TICKET_CHANNEL_ID" : 1392530165770227884,
    "REWARD_PRESET_CHANNEL_ID": 1403470024819085402,
    "REWARD_PRESET_ARCHIVE_CHANNEL_ID": 1403470095682109500
}

# Production config (Railway)
PROD_CONFIG = {
    "MOD_ROLE_IDS": [
        930538612754382869, 849835131182383145, 1386917677389582427
    ],
    "EMBED_CHANNEL_ID": 857618496103514177,  # Prod embed archive channel
    "EVENT_ANNOUNCEMENT_CHANNEL_ID": 857618496103514177, # Prod bot annoucement channel
    "TICKET_CHANNEL_ID" : 891142997218037870,
    "REWARD_PRESET_CHANNEL_ID": 1405315008421695518,
    "REWARD_PRESET_ARCHIVE_CHANNEL_ID": 1405315075895590922
}


if ENV in {"dev", "tu"}:
    CONFIG = DEV_CONFIG
elif ENV in {"qa", "test", "staging"}:
    CONFIG = QA_CONFIG
elif ENV in {"prod", "production"}:
    CONFIG = PROD_CONFIG
else:
    CONFIG = DEV_CONFIG  # safe default


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
SUPPORTED_FIELDS = {"url", "numeric_value", "text_value", "boolean_value", "date_value"}

# Pagination settings
ACTIONS_PER_PAGE = 5           # Admin action listing
EVENTS_PER_PAGE = 5            # Event listing
REWARDS_PER_PAGE = 5           # Shop reward listing
LOGS_PER_PAGE = 5              # Event/user logs


# Reward types to set mandatory fields
BADGE_TYPES = ("badge",)
STACKABLE_TYPES = ("preset", "dynamic",)
PUBLISHABLE_REWARD_TYPES = ("preset", "dynamic",)

EXCLUDED_LOG_FIELDS = {"created_by", "created_at", "modified_by", "modified_at", "preset_by", "preset_at"}



# ✅ Custom Discord emoji: <:name:id> or <a:name:id>
# name: 2–32 chars, letters/numbers/underscore; id: discord snowflake (17–20 digits)
CUSTOM_DISCORD_EMOJI = regex.compile(
    r"^<a?:[A-Za-z0-9_]{2,32}:\d{17,20}>$"
)

# ✅ Unicode emoji (single grapheme, supports ZWJ sequences + optional VS)
# Covers most modern emoji via Extended_Pictographic.
UNICODE_EMOJI = regex.compile(
    r"^(?:\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?"
    r"(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*"
    r"|\d\uFE0F\u20E3|[#*]\uFE0F\u20E3)$",
    flags=regex.VERSION1,
)