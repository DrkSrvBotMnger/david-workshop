# ✅ Event CRUD Tests – Coverage Summary

This document outlines the test coverage for the `bot.crud` event-related database functions.

---

## 🧪 Files

- `tests/test_crud_events.py`: Core logic tests
- `tests/test_crud_events_extended.py`: Optional fields, filters, logs, and edge cases

---

## 🔍 Covered Functions (from `bot.crud`)

| Function                  | Covered ✓ | Notes |
|---------------------------|-----------|-------|
| `create_event()`          | ✅        | Required and optional fields, timestamps |
| `get_event()`             | ✅        | Exists and not found |
| `update_event()`          | ✅        | Field updates, log reason, fail if not found |
| `delete_event()`          | ✅        | Deletion logic, log reason, fail if not found |
| `get_all_events()`        | ✅        | Filter by `tag`, `visible`, `active`, `mod_id` |
| `get_all_event_logs()`    | ✅        | Filter by `action`, `moderator` |

---

## ✅ Test Scenarios

### 🔹 Event Creation
- Required fields only
- Optional fields (end_date,coordinator, tags, shop section, embed fields, role)
- Timestamps (`created_at`) populated

### 🔹 Event Update
- Updates `modified_by`, `modified_at`
- Updates `tags`, `priority`, etc.
- Optional field clearing (`tags = None`) supported
- Update non-existent event returns `None`
- Reason included in log entry

### 🔹 Event Deletion
- Deletes successfully
- Deleting non-existent event returns `False`
- Reason included in log entry
  
### 🔹 Event Filtering
- By tag (removing spaces correctly)
- By `visible = True`
- By `active = True`
- By `mod_id` (creator or editor)

### 🔹 Event Logs
- `create`, `edit`, and `delete` actions logged
- Log reason text verified
- Filterable by:
  - `action`
  - `moderator`

---

## 📌 Notes

- Sorting by `created_at` in `get_all_events()` is not tested since final ordering is handled in the `/admin listevents` command logic.

---

_Last updated: July 25, 2025_