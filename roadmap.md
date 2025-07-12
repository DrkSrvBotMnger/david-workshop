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

## 🧩 Phase 0.5: SQLite Migration Plan (to replace JSON)

This phase runs **in parallel** with Phase 1, gradually moving away from JSON persistence.

- [ ] Install and configure `SQLAlchemy` for SQLite
- [ ] Create initial schema:
  - `users`, `events`, `actions`, `user_actions`, `user_event_data`
- [ ] Replace:
  - [ ] `get_user_data()` → DB call
  - [ ] `create_event()` → DB insert
  - [ ] `log_event_action()` → DB log
  - [ ] `get_events()` → DB query
- [ ] Add DB-based `/profile`, `/eventlist`, `/eventsubmit`
- [ ] Confirm that all legacy JSON calls are removed or refactored
- [ ] Implement backup/export feature (CSV or JSON dump for admin)

Eventually:
- [ ] Add `badges`, `titles`, `shop_items`, `purchases` to DB

---

## 🧠 Notes:
- JSON files will remain during transition, but eventually become read-only backups
- DB file will be stored as `data.db` (and excluded from Git)

---

## 🚧 Phase 1: Freeform Event System (current focus)

- [ ] type field added to events ("freeform", "bingo", "exchange")
- [ ] `create_event()` and admin command updated to support type
- [ ] User action logging system (user_actions.json)
- [ ] `/eventsubmit` — user self-logs an action
- [ ] `/eventmyscore` — user view of own score for current event
- [ ] `/eventleaderboard` — ranks users per event
- [ ] Showcase media (if configured in action)
- [ ] `/eventlogaction` (admin override to log for others)
- [ ] `/eventundoaction` (admin undo)
- [ ] Badge/title assigned on event join or completion

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

## 🧩 Phase 3: Event Types

- [ ] `freeform` – Custom actions (in progress)
- [ ] `bingo` – Prompt grid, track completions
- [ ] `exchange` – Sign-up, assignment, delivery
- [ ] Event type-specific logic loader

---

## 🧼 Maintenance Tasks

- [ ] Clean inactive users from `users.json`
- [ ] Backup logs externally (not in Git)
- [ ] Add type annotations in `utils.py`
- [ ] Expand error logging and validation

---

## 💡 Future Ideas

- Team-based point events
- Leaderboards by category (writing, art, etc.)
- Daily or weekly challenges
- `/eventinfo` command with banners, stats, timeline
- Profile badges as emojis with tooltips

---

_Last updated: July 12, 2025_
