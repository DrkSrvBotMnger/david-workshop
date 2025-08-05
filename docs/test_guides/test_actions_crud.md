# 🧪 Test Guide – Action CRUD Tests

This document outlines the test coverage for the `bot.crud.actions_crud` database functions.

---

## 📁 Files

* `tests/test_actions_crud.py`

---

## 🔍 Covered Functions

| Function                             | Covered ✓ | Notes                                  |
| ------------------------------------ | --------- | -------------------------------------- |
| `create_action()`                    | ✅         | Required + optional fields             |
| `get_action_by_key()`                | ✅         | Retrieval by public key                |
| `get_all_actions()`                  | ✅         | Unfiltered + filtered by `key_search`  |
| `delete_action()`                    | ✅         | Deletes existing, handles non-existent |
| `action_is_linked_to_active_event()` | ✅         | True + False cases                     |

---

## ✅ Test Scenarios

### 🔹 Action Creation

* Full dict creation, persisted fields verified
* Minimal fields creation, default values verified (`is_active=True`)
* Missing required `action_key` → raises `IntegrityError`

### 🔹 Action Retrieval

* Get by action key
* Get all actions
* Filtered by partial key match

### 🔹 Action Deletion

* Deletes existing action
* Non-existent action returns `False`

### 🔹 Linked to Active Event

* Linked → returns `True`
* Not linked → returns `False`

---

## 📌 Future Tests to Add

* Duplicate `action_key` rejection at CRUD level
* Filter by `is_active` in `get_all_actions`
* Ordering in `get_all_actions` (created\_at vs key)
* Update action function + logs if implemented later

---

_Last updated: August 4, 2025_