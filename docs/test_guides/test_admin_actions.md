# 🧪 Test Guide – Action Admin Command Tests

This document tracks the test coverage for `/admin_action`-related moderator commands. Each section includes a checklist of validated behaviors and suggestions for future tests.

---

## 📁 Files

- `tests/admin/test_create_action.py`
- `tests/admin/test_delete_action.py`
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

#### ⏳ Potential Additions
* [ ] Verify deletion prevents later retrieval via CRUD
* [ ] Verify deletion removes associated `ActionEventConfig` records (when implemented)

---

### 🧪 List Actions

#### 🔍 Covered Tests
* [x] Displays all actions in paginated embed 🔹 basic
* [x] Handles `input_fields_json` display with icons 🔹 basic

#### ⏳ Potential Additions
* [ ] Pagination >25 actions  
* [ ] Truncates overly long descriptions
* [ ] Correctly sorts actions alphabetically or by creation date

---

_Last updated: July 30, 2025_