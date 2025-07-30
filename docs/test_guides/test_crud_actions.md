# 🧪 Test Guide – Action CRUD Tests

This document outlines the test coverage for the `bot.crud` action-related database functions.

---

## 📁 Files

- `tests/crud/test_crud_actions.py`

---

## 🔍 Covered Functions

| Function                  | Covered ✓ | Notes |
|---------------------------|-----------|-------|
| `create_action()`         | ✅        | Required + optional fields, timestamps tested |
| `get_action_by_key()`     | ✅        | Basic retrieval by key |
| `get_action_by_id()`      | ✅        | Retrieval by numeric ID |
| `delete_action()`         | ✅        | Deletion logic |
| `get_all_actions()`       | ✅        | Full table retrieval |

---

## ✅ Test Scenarios

### 🔹 Action Creation
- [x] Creates valid action successfully 🔹 basic
- [x] Persists all required fields 🔹 basic
- [x] Accepts `input_fields_json=None`
- [x] Timestamps set automatically 🔹 basic

### 🔹 Action Deletion
- [x] Deletes existing action 🔹 basic
- [x] Returns `False` when deleting non-existent action 🔹 basic

### 🔹 Action Retrieval
- [x] Retrieves by key 🔹 basic
- [x] Retrieves by ID 🔹 basic
- [x] Retrieves all 🔹 basic

---

## 📌 Future Tests to Add
- [ ] Rejects duplicate `action_key` at CRUD level
- [ ] Handles invalid JSON in `input_fields_json`
- [ ] Ordering of `get_all_actions()` (by creation date desc)
- [ ] CRUD-level validation that `input_fields_json` matches allowed schema values

---

_Last updated: July 30, 2025_
