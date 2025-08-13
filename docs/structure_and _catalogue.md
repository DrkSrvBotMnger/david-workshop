# Folder Structure

```
├─ bot/
│  ├─ cogs/
│  │  ├─ admin/
│  │  │  ├─ prompts_cog.py              # clean             
│  │  │  ├─          
│  │  │  ├─          
│  │  │
│  │  ├─ users                  
│  │     ├─ profile_cog.py              # clean 
│  │     ├─ event_cog.py                # clean 
│  │
│  ├─ crud/
│  │  ├─ users_crud.py                  # partially clean
│  │  ├─ events_crud.py                 # partially clean
│  │  ├─ inventory_crud.py              
│  │  ├─ rewards_crud.py                # partially clean
│  │  ├─ action_events_crud.py          
│  │  ├─ user_actions_crud.py           # clean     
│  │  ├─ user_event_data_crud.py        # clean         
│  │  └─ prompts_crud.py                # clean
│  │
│  ├─ services/
│  │  ├─ events_service.py              # clean
│  │  ├─ action_events_service.py       # clean       
│  │  ├─ prompts_service.py                 
│  │  ├─ inventory_service.py              
│  │  ├─ rewards_service.py             # clean 
│  │  ├─ user_actions_service.py        # clean              
│  │  └─ users_service.py               # clean
│  │
│  ├─ presentation/
│  │  ├─ profile_presentation.py        # clean
│  │  ├─ events_presentation.py         # clean
│  │  ├─ actions_presentation.py        # clean
│  │  ├─ user_actions_presentation.py   # clean
│  │  ├─                
│  │
│  ├─ ui/
│  │  ├─ admin/
│  │  │  ├─ prompts_views               #clean             
│  │  │  ├─          
│  │  │  ├─          
│  │  │
│  │  ├─ user/
│  │  │  ├─ profile_views.py            # clean
│  │  │  ├─ inventory_views.py          
│  │  │  ├─ equip_title_view.py         
│  │  │  ├─ equip_badge_view.py         
│  │  │  ├─ events_views.py             # clean
│  │  │  ├─ report_action_views.py      # clean
│  │  │  └─ shop_dashboard_view.py          
│  │  │
│  │  ├─ common/
│  │  │  ├─ selects.py                  # clean
│  │  │  └─                             
│  │  │  
│  │  └─ renderers/
│  │     ├─ profile_card.py             # clean
│  │     └─ badge_loader.py             # clean
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
* **CURRENCY** — display the currency name

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
* `build_help_text_list(help_map` — ActionEvent help map as a list
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

### bot/crud/events_crud.py

* `EventFilter` — generic search inputs (status/type/has\_embed/dates/priority/text/limit/offset).&#x20;
* `search_events(session, f)` — applies `EventFilter`, orders by priority/date/name.&#x20;
* `get_event_by_key(session, event_key)` — ORM lookup.&#x20;
* `get_event_message_refs_by_key(session, event_key)` → `EventMessageRefs` (event\_key, event\_name, embed\_channel\_discord\_id, embed\_message\_discord\_id).&#x20;

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

### bot/services/events_service.py

* `find_events_dto(...)` — core finder; wraps `search_events`, does CSV tag post-filter, maps to `EventDTO`. &#x20;
* `list_user_browseable_events(limit=25)` — visible/active with embeds only.&#x20;
* `list_user_reporting_events(limit=25)` — visible/active (no embed requirement).&#x20;
* `list_user_archived_events(limit=25, tags_any=None)` — archived with optional tag filter.&#x20;
* `get_event_dto_by_key(event_key)` — ORM → `EventDTO`.&#x20;
* `get_event_message_refs_dto(event_key)` — projection → `EventMessageRefsDTO`.&#x20;

---

## Presentation

### bot/presentation/events_presentation.py

* `EventOptionVM` — `{ value, label, description }` for selects.&#x20;
* `EventMessageVM` — `{ event_key, title, channel_id, message_id, message_url }` for preview.&#x20;
* `event_default_fmt(d)` / `event_with_status_fmt(d)` / `event_with_dates_fmt(d)` / `event_compact_admin_fmt(d)` — labeling policies.&#x20;
* `make_event_options(dtos, fmt=...)` — `EventDTO[]` → `EventOptionVM[]`.&#x20;
* `make_event_message_vm(refs, guild_id)` — `EventMessageRefsDTO` → `EventMessageVM`.&#x20;

---

## UI – Common

### bot/ui/common/selects.py

* `build_select_options_from_vms(vms, ...)` — generic VM→`discord.SelectOption[]` (100-char truncation).&#x20;
* `GenericSelectView(options, on_select, ...)` — reusable select view; delegates to async handler.&#x20;

---

## UI – Renderers (clean)

### bot/ui/renderers/badge\_loader.py

* `extract_badge_icons(emojis, session)` — emoji strings → images or fallbacks

### bot/ui/renderers/profile\_card.py

* `generate_profile_card(user_avatar_bytes, display_name, points, total_earned, title, badges)` — final profile card image

---

## UI – Views

### bot/ui/user/profile\_views.py

* Main profile UI: buttons for inventory, equip title, equip badges

### bot/ui/user/inventory\_views.py

* Inventory display & navigation
* Preview display and navigation

### bot/ui/user/equip\_title\_view\.py

* Title select & equip handling

### bot/ui/user/equip\_badge\_view\.py

* Badge multi-select & equip handling

### bot/ui/user/events_views.py

* `make_user_event_select_view(vms, on_select)` — builds a select from `EventOptionVM`.&#x20;
* `UserEventButtons(guild_id, back_to_list=None)` — “Contact Mods” link + Back button (calls back to the cog to re-render the list).&#x20;

---

## Cogs (clean)

### bot/cogs/user/profile\_cog.py

* `/profile` — show profile card with equip buttons
* `/inventory` — show inventory list with preview publishable button
* `/equip_title` — open title equip view
* `/equip_badge` — open badge equip view

### bot/cogs/user/event_cog.py

* `/event` — initial select (followup.send) → on select: fetch original message and **edit** the same ephemeral to show the event preview + buttons; Back restores the select. &#x20;
* `/report_action` command; builds the initial view via `make_event_select_view`.

---

# WIP / To Refactor

* **bot/crud/users\_crud.py** — parts beyond identity helpers need review/cleanup
* **bot/ui/common/confirms.py** — old confirm view
* **bot/ui/common/paginator.py** — old paginator implementation
* Other CRUD/services/UI in admin/events/rewards/actions/shop flows not yet reviewed





# Catalogue (modules & responsibilities)

**Cogs**


**UI**

* `bot/ui/common/selects.py` — `GenericSelectView`, `build_select_options_from_vms`.
* `bot/ui/user/report_action_views.py` — view builders (`make_event_select_view`, `make_action_select_view`) and `ReportActionModal` (discord.py 2.x `TextInput`).

**Presentation**

* `bot/presentation/user_actions_presentation.py`

  * VMs: `EventPickVM`, `ActionOptionVM`.
  * Builders: `get_event_pick_vms`, `get_event_and_action_vms`.
  * Wrapper: `submit_report_action_presentation(member, …)` (opens DB session, builds DTO, calls service).

**Services**

* `bot/services/user_actions_service.py` — `submit_user_action`: validates rules, logs action, adds points, grants direct reward, **commit**.
* `bot/services/action_events_service.py` — `list_user_doable_action_events`: user scoping, event gating, repeatability filtering.
* `bot/services/events_service.py` — `list_user_reporting_events`, `get_event_dto_by_key`, `get_status_name`, `get_event_is_open_for_action`.
* `bot/services/rewards_service.py` — ORM→DTO (`RewardGrantDTO`), bump counters.
* (others present but not central to this flow: `inventory_service.py`, `users_service.py` for DTO fetch.)

**CRUD (single‑table only)**

* `action_events_crud.py` — list/filter AE rows; `get_action_event_bundle`; repeatability check.
* `user_actions_crud.py` — insert into `user_actions`.
* `user_event_data_crud.py` — ensure/create per‑event user row; increment event points.
* `users_crud.py` — `add_points_to_user`, `get_or_create_user` (used by users\_service).
* `rewards_crud.py` — fetch reward by reward\_event\_id; increment number\_granted.
* `inventory_crud.py` — add/increment inventory.
* `events_crud.py` — `get_event_by_key`, `list_user_reporting_events`.

**Domain**

* `bot/domain/dto.py` — `ActionEventDTO`, `UserActionCreateDTO`, `ActionReportResultDTO`, `RewardGrantDTO`.
* `bot/domain/mapping.py` — `to_action_event_dto`, `reward_to_grant_dto`.

**Utils**

* `bot/utils/parsing.py` — `parse_required_fields`, `parse_help_texts`.
* `bot/utils/...` — (time helpers, formatting, etc., as already in your tree).