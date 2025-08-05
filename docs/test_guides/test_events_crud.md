# 🧪 Test Guide – Event CRUD Tests

This document outlines the test coverage for the `bot.crud.events_crud` database functions.

---

## 📁 Files

* `tests/test_events_crud.py`

---

## 🔍 Covered Functions

| Function             | Covered ✓ | Notes                                             |
| -------------------- | --------- | ------------------------------------------------- |
| `create_event()`     | ✅         | Required + optional fields, timestamps            |
| `get_event_by_key()` | ✅         | Retrieval by public key                           |
| `get_all_events()`   | ✅         | Unfiltered + filtered by `event_status`           |
| `is_event_active()`  | ✅         | True + False cases                                |
| `update_event()`     | ✅         | Updates fields, logs reason, handles non-existent |
| `set_event_status()` | ✅         | Changes status, logs, handles non-existent        |
| `delete_event()`     | ✅         | Deletes + logs reason, handles non-existent       |
| `get_event_logs()`   | ✅         | Unfiltered + filtered by `log_action`             |

---

## ✅ Test Scenarios

### 🔹 Event Creation

* Full dict creation, persisted fields verified
* Minimal fields creation, default values verified (`priority=0`, `event_status=draft`)
* Missing required `event_key` → raises `IntegrityError`
* `created_at` matches log `performed_at` (timestamp consistency)

### 🔹 Event Retrieval

* Get by event key
* Get all events
* Filtered by `event_status`

### 🔹 Event Active Check

* Active event returns `True`
* Non-active event returns `False`

### 🔹 Event Update

* Updates with dict changes field values
* Reason text included in log entry
* `modified_at` matches log `performed_at`
* Update non-existent event returns `None`

### 🔹 Set Event Status

* Updates `event_status`
* Reason logged
* `modified_at` matches log `performed_at`
* Non-existent event returns `None`

### 🔹 Event Deletion

* Deletes existing event, logs reason
* Non-existent event returns `False`

### 🔹 Event Logs

* Retrieves all logs
* Filters logs by `log_action`

---

## 📌 Future Tests to Add

* Filter by `tag`
* Filter by `mod_by_discord_id`
* Filter by `event_status` combined with another filter
* Ensure events with linked rewards/actions can’t be deleted without proper cascade

---

_Last updated: August 4, 2025_