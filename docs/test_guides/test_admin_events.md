# ✅ Test Coverage – David's Workshop Bot (Admin Commands)

This document tracks the test coverage for `/admin`-related commands. Each section includes a checklist of validated behaviors.

---

## 📁 File: `admin.py`

### 🧪 `/admin createevent`

#### ✅ Covered Tests

* [x] Invalid start date shows correct error message
* [x] Invalid end date shows correct error message
* [x] Duplicate event ID is blocked
* [x] Coordinator defaults to command user
* [x] Event ID is correctly generated from shortcode and start date
* [x] `embed_channel_id` falls back to `EMBED_CHANNEL_ID` if not specified
* [x] Success message includes coordinator and event ID

#### ⏳ Potential Additions

* [ ] Invalid priority (non-int or negative)
* [ ] Tags parsing and trimming
* [ ] Shop section ID inclusion validation
* [ ] Embed channel argument (correct ID capture)

---

### 🧪 `/admin editevent`

#### ✅ Covered Tests

* [x] CLEAR removes `tags` when provided
* [x] Blocks edits to active events

#### ⏳ Potential Additions

* [ ] CLEAR removes `end_date`, `role_id`, `priority`, `shop_section_id`, `embed_message_id`
* [ ] Blocks clearing embed\_message\_id on visible event
* [ ] Partial update (only 1 field)
* [ ] No valid fields = rejection message
* [ ] Valid reason is logged

---

### 🧪 Authorization

#### ✅ Covered Tests

* [x] `is_admin_or_mod()` returns `False` for non-privileged user (logic test only)

#### ⏳ Potential Additions

* [ ] Positive logic test (admin = True)
* [ ] Positive logic test (mod role = True)
* [ ] Actual decorator behavior via registered command (if integration testing possible)

---
