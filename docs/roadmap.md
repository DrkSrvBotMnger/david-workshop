# 📈 Roadmap – David's Workshop Bot

Tracking development phases, feature sets, and future ideas.

---

## ✅ Completed

- Profile system (points, equipped title, badges)
- Event system with metadata, logs, visibility flags
- Reward shop, warehouse viewer, and linking to events
- Admin/mod commands for manual actions
- Paginated embeds and user-friendly navigation

---

## 🧩 Phase 0.5: SQLite Migration Plan + Setting automated testing tools

### 🧪 SQLite Migration

- [✅️] Install and configure `SQLAlchemy` for SQLite
- [✅️] Create initial schema for `User`, `Event`, `Inventory`, `UserEventData`, `Action`, `ActionEventConfig`, `UserAction`
- [✅️] Check potential missing metadata 
- [ ] Create remaining tables schema for Reward and EventReward
- [ ] Create database.py for engine/session management.
- [ ] Create init_db.py for table creation testing.
	 
### ✅ Tests Setup

- [ ] Create `/tests/` directory in project
- [ ] Set up Python’s `unittest` framework
- [ ] Add base test runner script: `python3 -m unittest discover tests`
- [ ] (Optional) Install `pytest` for improved output formatting

### 🧹 Data Generation

- [ ] `tests/fake_data.py`
    - [ ] `generate_fake_users(count=5)`
    - [ ] `generate_fake_events(count=3)`
- [ ] (Optional) `tests/truncate_db.py` to clear DB between test runs


---

## 🧠 Notes:
- DB file will be stored as `data.db` (and excluded from Git)

---

## 🚧 Phase 1: Freeform Event System (current focus)

- [ ] Refactor current bot commands to work with the new schemas
    - [ ] `/profile`	
    - [ ] `/createevent`
    - [ ] `/editevent`
    - [ ] `/deleteevent`
    - [ ] `/eventlog`
    - [ ] `/addreward`
    - [ ] `/editreward`
    - [ ] `/removereward` (rename deletereward)
    - [ ] `/listwarehouse` (rename warehouse)
    - [ ] `/eventlinkreward`
    - [ ] `/eventunlinkreward`
    - [ ] `/givepoints`
    - [ ] `/removepoints` (rename takepoints)
    - [ ] `/givereward`
    - [ ] `/takereward`
    - [ ] `/rewardinfo`
	- [ ] `/eventmenu`
	- [ ] `/eventlist`
	- [ ] `/rewardhistory to show case both history of points and rewards in and out
- [ ] Create a reward log akin to the event log
- [ ] `/createaction`, and `/deleteaction` 
- [ ] `/actioneventconfig` - admin command to define actions that can be done, points and item granted, self-log status and input help for a specific event
- [ ] `/action` Command System
	- [ ] `/action list event:<event>` Display available actions with input_help_text from ActionEven.tConfig.
	- [ ] `/action perform` Validate and log user action based on Action definitions.
- [ ] User action logging system with CRUD functions:
	- [ ] Log actions with standardized data (url, numeric, text, boolean, date).
- Create `/equip` command to equipe titles (limite 1), or badges (limite 10?). Item aren't equipable yet.


### 🧪 Tests with Phase 1

- [ ] `test_users.py`
    - [ ] Users are created successfully
    - [ ] Points are valid integers
    - [ ] No duplicate Discord IDs

- [ ] `test_events.py`
    - [ ] Event creation works with correct structure
    - [ ] Default values for `active` and `visible` are respected
    - [ ] Event creation, edition and deletion are correctly logged
	- [ ] Event creation only support `freeform`for now
	
- [ ] `test_actions.py` (after `user_actions` table exists)
    - [ ] User actions log correctly
    - [ ] Points are calculated and stored
    - [ ] Admin action logging functions correctly

- [ ] `test_profiles.py`
    - [ ] Profile fetch reflects correct totals
    - [ ] Equipped title is tracked properly
    - [ ] Handles empty profiles gracefully

- [ ] Reflect on any other needed test cases

---

## 🎮 Phase 2: Profile Rework, Gamification & Shop Expansion

- [ ] Store total_points_earned, total_points_spent
- [ ] Add event history to user profiles (events joined, points earned)
- [ ] /profile shows:
  - [ ] Active title
  - [ ] Badges (with emoji)
  - [ ] Points (current / earned)
  - [ ] Events attended
- [ ] Add /badges to view full badge list
- [ ] `/shop` to browse items
- [ ] `/buy` to spend points
- [ ] `/inventory` for titles/badges/items
- [ ] `/equip title` to change public title
- [ ] Badge & title visuals in `/profile`

---

## 🎄 Phase 3: Event Types & Structured Signup

- [ ] Add `bingo` event logic: prompt grid, per-prompt scoring
- [ ] Add `exchange` event logic: signup + assignment + completion
- [ ] `/eventsignup` — structured signup command for exchange-type events
    - [ ] AO3, Tumblr, email, DNWs, preferences
    - [ ] Stored securely in `user_event_data`
- [ ] Cleanup tool: `/cleansensitive @event` to remove AO3/email/etc.
    - [ ] Mod-only command
    - [ ] Clears fields post-event or by request

---

## 🧼 Maintenance Tasks

- [ ] Clean inactive users from `users.json`
- [ ] Backup logs externally (not in Git)
- [ ] Add type annotations in `utils.py`
- [ ] Expand error logging and validation

---

## Phase 4: Core Test Suites & Developer Safety Nets

### 🔧 Developer Tooling

- [ ] Add testing instructions to `dev-notes.md`
- [ ] (Optional) Create `pytest.ini` with:
- [ ] Configure Replit “Tests” tab to run suite automatically (optional)

### 🧘 Future-Safe Practices

- [ ] Run full test suite before schema changes or major updates
- [ ] Add regression tests
- [ ] Write validation tests for bingo, exchange, and other new event types

_Last updated: July 12, 2025_
