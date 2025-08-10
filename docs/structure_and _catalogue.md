# Folder Structure

```
├─ bot/
│  ├─ cogs/
│  │  └─ user/
│  │     ├─ profile_cog.py              # /profile, /inventory, /equip_title, /equip_badge are clean 
│  │
│  ├─ ui/
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
│  │  ├─ profile_service.py             # clean
│  │  ├─ equip_service.py               # clean
│  │  └─ users_service.py                # clean
│  │
│  ├─ crud/
│  │  ├─ users_crud.py                  # partially clean (identity helpers OK)
│  │  └─ inventory_crud.py              # clean
│  │
│  ├─ domain/
│  │  ├─ dto.py                         # clean
│  │  └─ mapping.py                     # clean
│  │
│  ├─ utils/
│  │  ├─ discord_helpers.py             # clean
│  │  ├─ formatting.py                  # clean
│  │  ├─ parsing.py                     # clean
│  │  ├─ permissions.py                 # clean
│  │  └─ emoji.py                       # clean
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
├─ assets/
│  ├─ backgrounds/
│  ├─ fonts/
│  ├─ sources/
│  └─ twemoji/
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

## Config

### bot/config/constants.py

* **ALLOWED\_ACTION\_INPUT\_FIELDS**, **SUPPORTED\_FIELDS** — allowed input fields for Action definitions (list/set)
* **ACTIONS\_PER\_PAGE**, **EVENTS\_PER\_PAGE**, **REWARDS\_PER\_PAGE**, **LOGS\_PER\_PAGE** — paginator sizes
* **BADGE\_TYPES**, **STACKABLE\_TYPES**, **PUBLISHABLE\_REWARD\_TYPES** — reward categorization
* **EXCLUDED\_LOG\_FIELDS** — fields to skip when comparing for logs
* **CUSTOM\_DISCORD\_EMOJI**, **UNICODE\_EMOJI** — emoji regex patterns
* **MAX\_BADGES** — display limit on profile

### bot/config/environments.py

* **MOD\_ROLE\_IDS** — moderator role IDs
* **EVENT\_ANNOUNCEMENT\_CHANNEL\_ID**, **TICKET\_CHANNEL\_ID**, **REWARD\_PRESET\_CHANNEL\_ID**, **REWARD\_PRESET\_ARCHIVE\_CHANNEL\_ID** — specific channel IDs (embed ID pending validation)

---

## Utils

### bot/utils/discord\_helpers.py

* `resolve_display_name(user_row)` — best display name for user
* `post_announcement_message(interaction, announcement_channel_id, msg, role_discord_id=None)` — send announcement

### bot/utils/emoji.py

* `is_custom_emoji(s)` — check for custom Discord emoji (uses `CUSTOM_DISCORD_EMOJI`)
* `emoji_to_codepoint(emoji)` — Unicode emoji → Twemoji codepoint

### bot/utils/formatting.py

* `now_iso()` — UTC now in ISO 8601
* `now_unix()` — UTC now as Unix timestamp
* `format_discord_timestamp(iso_str, style="F")` — ISO datetime → Discord timestamp token
* `format_log_entry(...)` — standard log line for embeds/paginators

### bot/utils/parsing.py

* `safe_parse_date(date_str)` — YYYY-MM-DD or None
* `parse_required_fields(input_fields_json)` — ordered required fields
* `parse_help_texts(input_help_text, fields)` — ActionEvent help texts as dict
* `parse_message_link(message_link)` — Discord link → (channel\_id, message\_id)

### bot/utils/permissions.py

* `is_admin_or_mod(interaction)` — admin or mod role check
* `admin_or_mod_check()` — decorator for commands needing admin/mod

---

## Domain

### bot/domain/dto.py

* DTOs for user/profile view models (`UserDTO`, `ProfileVM` etc.)

### bot/domain/mapping.py

* ORM ↔ DTO mapping functions

---

## CRUD (clean only)

### bot/crud/inventory\_crud.py

* `reward_type_order()` — ordering by type (title→badge→preset→other)
* `fetch_user_inventory_ordered(session, user_id)` — rows shaped for UI
* `get_equipped_title_name(session, user_id)` — equipped title name
* `get_equipped_badge_emojis(session, user_id)` — equipped badge emojis list
* `fetch_user_titles_for_equip(session, user_id)` — (reward\_key, reward\_name, is\_equipped) list
* `fetch_user_badges_for_equip(session, user_id)` — (reward\_key, reward\_name, emoji, is\_equipped) list
* `set_titles_equipped(session, user_id, selected_key)` — equip 0/1 title
* `set_badges_equipped(session, user_id, selected_keys)` — equip multiple badges

---

## Services (clean)

### bot/services/users\_service.py

* `get_or_create_user_dto(member)` — ensure user exists/updated, return DTO

### bot/services/profile\_service.py

* `fetch_profile_vm(member)` — aggregate profile VM (user, equipped items, display name)
* `build_profile_file(vm)` — generate profile card image & return (file, display\_name)

### bot/services/equip\_service.py

* `get_title_select_options(user_id)` — title select for equip UI
* `get_badge_select_options(user_id)` — badge select for equip UI

### bot/services/inventory\_service.py

* `get_user_publishables_for_preview(session, user_id)` -> Dict[str, Tuple[str, str, str]]
    * Builds a select map for previewing publishable rewards:
    * reward_key → (channel_id, message_id, label).
    * Filters by PUBLISHABLE_REWARD_TYPES and requires both pointers.

---

## UI – Renderers (clean)

### bot/ui/renderers/badge\_loader.py

* `extract_badge_icons(emojis, session)` — emoji strings → images or fallbacks

### bot/ui/renderers/profile\_card.py

* `generate_profile_card(user_avatar_bytes, display_name, points, total_earned, title, badges)` — final profile card image

---

## UI – Views (clean)

### bot/ui/user/profile\_views.py

* Main profile UI: buttons for inventory, equip title, equip badges

### bot/ui/user/inventory\_views.py

* Inventory display & navigation
* Preview display and navigation

### bot/ui/user/equip\_title\_view\.py

* Title select & equip handling

### bot/ui/user/equip\_badge\_view\.py

* Badge multi-select & equip handling

---

## Cogs (clean)

### bot/cogs/user/profile\_cog.py

* `/profile` — show profile card with equip buttons
* `/inventory` — show inventory list with preview publishable button
* `/equip_title` — open title equip view
* `/equip_badge` — open badge equip view

---

# WIP / To Refactor

* **bot/crud/users\_crud.py** — parts beyond identity helpers need review/cleanup
* **bot/ui/common/confirms.py** — old confirm view
* **bot/ui/common/paginator.py** — old paginator implementation
* Other CRUD/services/UI in admin/events/rewards/actions/shop flows not yet reviewed
