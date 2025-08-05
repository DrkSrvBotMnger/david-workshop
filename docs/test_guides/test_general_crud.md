Here’s the **general CRUD** test doc based on your current `test_general_crud.py`.

---

# 🧪 Test Guide – General CRUD Tests

This document outlines the test coverage for the `bot.crud.general_crud` utility functions.
These functions are shared across all CRUD modules.

---

## 📁 Files

* `tests/test_general_crud.py`

---

## 🔍 Covered Functions

| Function                      | Covered ✓ | Notes                                       |
| ----------------------------- | --------- | ------------------------------------------- |
| `log_change()`                | ✅         | Standard logging and forced-change logging  |
| `is_linked_to_active_event()` | ✅         | True + False cases for active event linking |

---

## ✅ Test Scenarios

### 🔹 log\_change()

* Creates log entry with correct details
* Handles `forced=True` and prefixes description with `⚠️ **FORCED CHANGE**`

### 🔹 is\_linked\_to\_active\_event()

* Returns `True` when object is linked to at least one active event
  (tested with `RewardEvent` as example)
* Returns `False` when no active event link exists

---

## 📌 Future Tests to Add

* Timestamp consistency between `modified_at`/`created_at` and log `performed_at` for all calling CRUDs
  *(currently verified in reward/event tests instead)*
* Additional linked-object cases:

  * `ActionEvent`
  * Other link models if added in the future

---

_Last updated: August 4, 2025_