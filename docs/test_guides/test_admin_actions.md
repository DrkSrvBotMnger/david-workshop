# 🧪 Test Guide – Action Admin Command Tests

This document tracks the test coverage for `/admin_action`-related moderator commands. Each section includes a checklist of validated behaviors and suggestions for future tests.

---

## 📁 Files

- `tests/admin/test_create_action.py`
- `tests/admin/test_delete_action.py`
- `tests/admin/test_deactivate_action.py
- `tests/admin/test_list_action.py`

---

### 🧪 Create Action

#### 🔍 Covered Tests
* [x] Creates a new action successfully with valid input 🔹 basic
* [x] Rejects duplicate `action_key` 🔹 basic
* [x] Rejects invalid `input_fields` values 🔹 basic
* [x] Properly sends moderator feedback message 🔹 basic

#### ⏳ Potential Additions
* [ ] Rejects invalid `action_key` format (uppercase, spaces, special chars)
* [ ] Rejects overly long description (> safe embed limit)
* [ ] Validates `input_fields` set matches allowed schema values exactly

---

### 🧪 Delete Action

#### 🔍 Covered Tests
* [x] Deletes an existing action successfully 🔹 basic
* [x] Rejects deletion of a non-existent action 🔹 basic
* [x] Rejects deletion if action is inactive 🔹 basic
* [x] Rejects deletion if action is referenced in user history (UserAction) 🔹 basic

#### ⏳ Potential Additions
* [ ] Verify deletion removes associated `ActionEventConfig` records (when implemented)

---

### 🧪 Deactivate Actions

#### 🔍 Covered Tests
* [x] Successfully deactivates an active action → sets active=False, renames key with _v1, sets deactivated_at 🔹 basic
* [x] Rejects deactivation if action is already inactive 🔹 basic
* [x] Rejects deactivation if action does not exist 🔹 basic

#### ⏳ Potential Additions
* [ ] Handles multiple previous versions → correctly increments to _vN

---

### 🧪 List Actions

#### 🔍 Covered Tests
* [x] Displays all actions in paginated embed 🔹 basic
* [x] Handles `input_fields_json` display with icons 🔹 basic

#### ⏳ Potential Additions
* [ ] Pagination >25 actions  
* [ ] Truncates overly long descriptions
* [ ] Correctly sorts actions alphabetically or by creation date
* [ ] Pagination triggers when more than ACTIONS_PER_PAGE actions
* [ ] Shows inactive actions with show_inactive=True → red status icon
* [ ] Alphabetical sorting confirmed
* [ ] Long descriptions truncated to avoid embed limit

---

_Last updated: July 30, 2025_