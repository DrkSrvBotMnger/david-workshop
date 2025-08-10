# Folder Structure
```
├─ bot/
│  ├─ app.py
│  ├─ cogs/
│  │  ├─ admin/
│  │  │  ├─ events_cog.py
│  │  │  ├─ rewards_cog.py
│  │  │  ├─ actions_cog.py
│  │  │  └─ shop_cog.py
│  │  └─ user/
│  │     ├─ profile_cog.py              # /profile, /inventory are clean 
│  │     ├─ event_cog.py
│  │     └─ shop_cog.py
│  │
│  ├─ ui/
│  │  ├─ common/
│  │  │  ├─ base_view.py
│  │  │  ├─ paginator.py                # to redo probably
│  │  │  └─ confirms.py                 # to redo probably
│  │  ├─ admin/
│  │  │  ├─ events_views.py
│  │  │  ├─ rewards_views.py
│  │  │  ├─ actions_views.py
│  │  │  └─ shop_views.py
│  │  ├─ user/
│  │  │  ├─ profile_views.py            # clean
│  │  │  ├─ inventory_views.py          # clean
│  │  │  ├─ equip_title_view.py         # clean
│  │  │  └─ equip_badge_view.py         # clean
│  │  └─ renderers/
│  │     ├─ profile_card.py             # clean
│  │     └─ badge_loader.py             # clean
│  │
│  ├─ services/
│  │  ├─ events_service.py
│  │  ├─ rewards_service.py
│  │  ├─ actions_service.py
│  │  ├─ shop_service.py
│  │  ├─ profile_service.py				# clean
│  │  ├─ inventory_service.py			# clean
│  │  └─ users_service.py
│  │
│  ├─ crud/
│  │  ├─ events_crud.py
│  │  ├─ rewards_crud.py
│  │  ├─ actions_crud.py
│  │  ├─ action_events_crud.py
│  │  ├─ reward_events_crud.py
│  │  ├─ users_crud.py
│  │  └─ inventory_crud.py              # clean
│  │
│  ├─ domain/
│  │  ├─ dto.py                        # clean
│  │  ├─ validators.py    
│  │  └─ mapping.py                    # clean
│  │
│  ├─ utils/
│  │  ├─ discord_helpers.py             # clean
│  │  ├─ formatting.py                  # clean
│  │  ├─ parsing.py                     # clean
│  │  ├─ permissions.py                 # clean
│  │  ├─ emoji.py                       # clean
│  │  └─ logging.py
│  │
│  └─ config/
│     ├─ __init__.py                    # clean
│     ├─ environments.py                # clean
│     └─ constants.py                   # clean
│
├─ db/
│  ├─ database.py
│  ├─ schema.py
│  └─ migrations/
│
├─ tests/
│  ├─ cogs/
│  ├─ services/
│  ├─ crud/
│  ├─ ui/
│  └─ utils/
└─ docs/
```

# Catalogue

## bot/config/constants.py  

- ALLOWED_ACTION_INPUT_FIELDS, SUPPORTED_FIELDS
    - Allowed input fields for Action definitions (in list or set)
- ACTIONS_PER_PAGE, EVENTS_PER_PAGE, REWARDS_PER_PAGE, LOGS_PER_PAGE
    - Nb of items per page in paginator
- BADGE_TYPES, STACKABLE_TYPES, PUBLISHABLE_REWARD_TYPES
    - Rewards organized by types
- EXCLUDED_LOG_FIELDS
    - Fields not to consider when checking for change before logging
- CUSTOM_DISCORD_EMOJI, UNICODE_EMOJI
    - Emoji regex
- MAX_BADGES
    - Display limit on profile

## bot/config/environments.py

- MOD_ROLE_IDS
    - Roles ids of moderators
- EMBED_CHANNEL_ID
    - Deprecated? to validate
- EVENT_ANNOUNCEMENT_CHANNEL_ID, TICKET_CHANNEL_ID, REWARD_PRESET_CHANNEL_ID, REWARD_PRESET_ARCHIVE_CHANNEL_ID
    - specific discord channels id

## bot/utils/parsing.py

- safe_parse_date(date_str: str) -- Optional[str]
    - Attempts to parse a date string into YYYY-MM-DD. Returns None if invalid.
- parse_required_fields(input_fields_json: Optional[str]) -- list[str]
    - Return ordered list of required fields Action definitions (subset of SUPPORTED_FIELDS).
- parse_help_texts(input_help_text: Optional[str], fields: list[str]) -- dict[str, str]
    - Turn the ActionEvent.input_help_text JSON (a list) into a dict:
    -   {"general": "...", <per-field...-}
    - The list is expected as: [general, <one per field in `fields` order-]
    - Missing/short lists are handled gracefully.
- parse_message_link(message_link: str) -- tuple[int, int]
    - Parse a Discord message link into (channel_id, message_id).
    - Raises ValueError if format is invalid.

## bot/utils/formatting.py

- now_iso() -- str
    - Current UTC time in ISO 8601 format with timezone offset.
- now_unix() -- int
    - Current UTC time as Unix timestamp (int).
- format_discord_timestamp(iso_str: str, style: str = "F") -- str
    - Format an ISO 8601 datetime string to a Discord timestamp token.
    - Returns the original string if parsing fails.
- format_log_entry(log_action: str, performed_by: str, performed_at: str, log_description: Optional[str] = None, label: Optional[str] = None) -- str:
    - Format a generic log entry for display in embeds or paginated lists.
    - `performed_at` expected as "%Y-%m-%d %H:%M:%S.%f" (falls back to raw string).

## bot/utils/permissions.py

- is_admin_or_mod(interaction: Interaction) -- bool
    - True if invoker is admin or has any role in MOD_ROLE_IDS.
- admin_or_mod_check() -- app_commands.check
    - Decorator for app commands that require admin or mod.

## bot/utils/emoji.py

- is_custom_emoji(s: Optional[str]) -- bool
    - Check if a string is a custom Discord emoji (e.g. <:name:id-).
- emoji_to_codepoint(emoji: str) -- str
    - Convert a Unicode emoji into Twemoji codepoint format (e.g. '1f600').

## bot/utils/discord_helpers.py

- resolve_display_name(user_row) -- str
    - Returns the most relevant display name for a user.
- post_announcement_message(interaction: discord.Interaction, announcement_channel_id: str, msg: str, role_discord_id: Optional[str] = None) -- Optional[Message]
    - Post announcement in announcement channel

## bot/ui/common/confirms.py

- class ConfirmActionView(ui.View)
    - Simple yes/no confirm view. Set .message after sending to enable timeout edits.
- confirm_action( interaction: discord.Interaction, item_name: str, item_action: str, reason: str | None = None) -- bool
    - Generic confirmation dialog.
    - Returns True if user confirmed, False otherwise.
    - Old version to be revised

## bot/ui/common/paginator.py

- class EmbedPaginator(View)
    - Simple embed paginator with first/prev/next/last controls.
    - Call with a prebuilt list of embeds.
    - Old version to be revised
- paginate_embeds(interaction: discord.Interaction, embeds: list[discord.Embed], ephemeral: bool = True)
    - Convenience helper to send a paginated embed message.
    - Old version to be revised

## bot/ui/renderers/badge_loader.py

- extract_badge_icons(emojis: List[str], session: aiohttp.ClientSession) -- List[Union[Image.Image, str]]
    - Given a list of emoji strings (custom or unicode),
    - return a list of Pillow Image objects or emoji strings as fallback.

## bot/ui/renderers/profile_card.py

- generate_profile_card( user_avatar_bytes: bytes, display_name: str, points: int, total_earned: int, title: str, badges: List[Union[Image.Image, str]]) -- io.BytesIO
    - Generate a profile card image from real data with emoji or image badges.

## bot/crud/inventory_crud.py

- reward_type_order() -- Case
    - Order rewards by type: title, badge, preset, other.
- fetch_user_inventory_ordered(session, user_id: int) -- list[dict]
    - Returns rows shaped for UI:
    - {
    -   "inv_id": int, "is_equipped": bool,
    -   "reward_id": int, "reward_key": str, "reward_type": str,
    -   "reward_name": str, "reward_description": str | None, "emoji": str | None,
    - }
- get_equipped_title_name(session, user_id: int) -- Optional[str]
    - Returns the name of the equipped title, or None if no title is equipped.
- get_equipped_badge_emojis(session, user_id: int) -- List[str]
    - Returns a list of emojis for equipped badges, or an empty list if no badges are equipped.
- fetch_user_titles_for_equip(session, user_id: int) -- list[tuple[str, str, bool]]
    - Returns [(reward_key, reward_name, is_equipped)]
- fetch_user_badges_for_equip(session, user_id: int) -- list[tuple[str, str, str | None, bool]]
    - Returns [(reward_key, reward_name, emoji, is_equipped)]

## bot/services/profile_service.py
- fetch_profile_vm(target_member) -- ProfileVM
    - Fetch a ProfileVM for a given member.
- build_profile_file(vm: ProfileVM) -- File
    - Generate a profile card image and return it as a File, along with the display name.

## bot/services/inventory_service.py
- fetch_inventory_for_member(target_member) -- (db_user_row, items)
    - Fetch user inventory for a given member.
    - Returns a tuple: (user_row, items, display_name)
  

# Flow-map

# docs/flow-map.yml

commands:
  /profile:
    cog: bot/cogs/user/profile_cog.py
    entrypoints:
      - handle_profile_command()
    services:
      - bot/services/profile_service.py: 
          - fetch_profile_vm()
          - build_profile_file()
    crud:
      - bot/crud/inventory_crud.py:
          - get_equipped_title_name()
          - get_equipped_badge_emojis()
      - bot/crud/users_crud.py:
      
    ui:
      views:
        - bot/ui/user/profile_views.py
      renderers:
        - bot/ui/renderers/profile_card.py
        - bot/ui/renderers/badge_loader.py



  /inventory:
    cog: bot/cogs/user/profile_cog.py
    entrypoints:
      - handle_inventory_command()
    services:
      - bot/services/inventory_service.py:
          - fetch_inventory_for_member()
    crud:
      - bot/crud/inventory_crud.py:
          - fetch_user_inventory_ordered()
    ui:
      views:
        - bot/ui/user/inventory_views.py
