# 🧪 Test Guide – Event Admin commands Tests

This document tracks the test coverage for `/admin`-related commands for events. Each section includes a checklist of validated behaviors.

---

## 📁 Files

- `tests/admin/test_create_event.py`
- `tests/admin/test_edit_event.py`
- `tests/admin/test_delete_event.py`

---

### 🧪 Create Event

#### 🔍 Covered Tests

* [x] Success message includes event name,  event ID and coordinator 🔹 basic
* [x] Invalid start date shows correct error message
* [x] Invalid end date shows correct error message
* [x] Duplicate event ID is blocked
* [x] Coordinator defaults to command user
* [x] Event ID is correctly generated from shortcode and start date
* [x] `embed_channel_id` falls back to `EMBED_CHANNEL_ID` if not specified
* [x] Embed channel argument (correct ID capture)
* [x] Tags parsing and trimming
* [x] Invalid priority if negative
* [x] Log entry is created with action `create`, including `performed_by` 🔹 basic

#### ⏳ Potential Additions

* [ ] Shop section ID inclusion validation (later when shop is set)

---

### 🧪 Edit Event

#### 🔍 Covered Tests

* [x] All editable fields apply correctly (name, description, dates, tags, role, etc.) 🔹 basic
* [x] All fields that accept `CLEAR` keyword work 🔹 basic
* [x] Priority accepts int and and goes back to 0 when `CLEAR` 🔹 basic
* [x] Reason is optional and appears in confirmation message if given
* [x] If only `event_id` and `reason` are provided, shows "no fields provided" error
* [x] `modified_by` and `modified_at` are populated 🔹 basic
* [x] Start date parsing and error on invalid format
* [x] End date parsing and error on invalid format
* [x] Event not found shows error
* [x] Active event cannot be edited 🔹 basic
* [x] Clearing `embed_message_id` is blocked if event is visible 🔹 basic
* [x] Embed channel and message ID are correctly accepted and stored
* [x] Tag updates preserve trimming and formatting
* [x] Log entry is created with action `edit`, including `reason` if provided and `performed_by` 🔹 basic

---

### 🧪 Delete Event

#### 🔍 Covered Tests

* [x] Success message includes event name and deletion confirmation 🔹 basic
* [x] Event not found shows error
* [x] Active event cannot be deleted 🔹 basic
* [x] Visible event cannot be deleted 🔹 basic
* [x] Log entry is created with action `delete`, including `reason` and `performed_by` 🔹 basic

#### ⏳ Potential Additions

* [ ] Simulate timeout to test UI behavior (e.g. buttons disabled after 60s)

---

### 🧪 Display Event

#### 🔍 Covered Tests

* [x] Successfully make event visible → success message includes event name and ID 🔹 basic
* [x] `modified_by` and `modified_at` populated 🔹 basic
* [x] Log entry created with action `edit` and correct `performed_by` 🔹 basic

#### ⏳ To be Added

* [ ] Event not found → error message
* [ ] Already visible → warning message
* [ ] Missing `embed_message_id` → error message
* [ ] Announcement sent to `EVENT_ANNOUNCEMENT_CHANNEL_ID`
* [ ] Role mention is included if event has `role_id`

---

### 🧪 Hide Event

#### 🔍 Covered Tests

* [x] Active event cannot be hidden → error message 🔹 basic
* [x] Successfully hide visible inactive event 🔹 basic
* [x] `modified_by` and `modified_at` populated 🔹 basic
* [x] Log entry created with action `edit` and correct description 🔹 basic

#### ⏳ To be Added

* [ ] Event not found → error message
* [ ] Already hidden → warning message

---

### 🧪 Activate Event

#### 🔍 Covered Tests

* [x] Successfully activate inactive event (sets `active=True`) 🔹 basic
* [x] Automatically sets `visible=True` if not visible 🔹 basic
* [x] `modified_by` and `modified_at` populated 🔹 basic
* [x] Log entry created with action `edit` and correct description 🔹 basic

#### ⏳ To be Added

* [ ] Event not found → error message
* [ ] Already active → warning message
* [ ] Missing `embed_message_id` → error message
* [ ] Announcement sent, includes `role_id` mention if present

---

### 🧪 Deactivate Event

#### 🔍 Covered Tests

* [x] Successfully deactivate active event 🔹 basic
* [x] `modified_by` and `modified_at` populated 🔹 basic
* [x] Log entry created with action `edit` and correct description 🔹 basic

#### ⏳ To be Added

* [ ] Event not found → error message
* [ ] Already inactive → warning message
* [ ] Announcement sent, includes `role_id` mention if present

---

### 🧪 List Events

#### 🔍 Covered Tests

* [x] Pagination works (more than 5 events) 🔹 basic

#### ⏳ To be Added

* [ ] Returns all events with no filters
* [ ] Filters by tag correctly
* [ ] Filters by `active=True` / `active=False`
* [ ] Filters by `visible=True` / `visible=False`
* [ ] Filters by `mod_name`
* [ ] Sorted newest to oldest by `modified_at` or `created_at`

---

### 🧪 Show Event

#### 🔍 Covered Tests

* [x] Displays all core metadata (dates, visibility, active, coordinator, tags, description, priority, shop section, embed link if exists) 🔹 **priority**

#### ⏳ To be Added

* [ ] Event not found → error message
* [ ] Correctly shows `created_by` and `modified_by` mentions
* [ ] Shows *Ongoing* if no end date
* [ ] Correct embed formatting (all fields populated)

---

### 🧪 Event Logs

#### 🔍 Covered Tests

* [x] Sorted most recent first 🔹 **priority**
* [x] Pagination works (more than 5 logs) 🔹 **priority**

#### ⏳ To be Added

* [ ] No logs found → error message
* [ ] Shows logs with no filters
* [ ] Filter by `action` works
* [ ] Filter by `moderator` works

---

_Last updated: July 29, 2025_