# 🧪 Test Guide – Reward CRUD Tests

This document outlines the test coverage for the `bot.crud.rewards_crud` database functions.

---

## 📁 Files

* `tests/test_rewards_crud.py`

---

## 🔍 Covered Functions

| Function                             | Covered ✓ | Notes                                                       |
| ------------------------------------ | --------- | ----------------------------------------------------------- |
| `create_reward()`                    | ✅         | Required + optional fields, timestamp checks                |
| `get_reward_by_key()`                | ✅         | Retrieval by public key                                     |
| `get_all_rewards()`                  | ✅         | Unfiltered + filtered by `reward_type`                      |
| `reward_is_linked_to_active_event()` | ✅         | True + False cases                                          |
| `update_reward()`                    | ✅         | Updates fields, logs reason, handles non-existent           |
| `publish_preset()`                   | ✅         | Updates preset fields, forced logging, handles non-existent |
| `delete_reward()`                    | ✅         | Deletes + logs reason, handles non-existent                 |
| `get_reward_logs()`                  | ✅         | Unfiltered + filtered by `log_action`                       |

---

## ✅ Test Scenarios

### 🔹 Reward Creation

* Full dict creation, persisted fields verified
* Minimal fields creation, default values verified
* Missing required `reward_key` → raises `IntegrityError`
* `created_at` matches log `performed_at` (timestamp consistency)

### 🔹 Reward Retrieval

* Get by reward key
* Get all rewards
* Filtered by `reward_type`

### 🔹 Linked to Active Event

* Linked → returns `True`
* Not linked → returns `False`

### 🔹 Reward Update

* Update with dict changes field values
* Reason text included in log entry
* `modified_at` matches log `performed_at`
* Update non-existent reward returns `None`

### 🔹 Publish Preset

* Updates preset fields
* Forced flag adds `⚠️ **FORCED CHANGE**` prefix
* `modified_at` matches log `performed_at`
* Non-existent reward returns `None`

### 🔹 Reward Deletion

* Deletes existing reward, logs reason
* Non-existent reward returns `False`

### 🔹 Reward Logs

* Retrieves all logs
* Filters logs by `log_action`

---

## 📌 Future Tests to Add

* Duplicate `reward_key` rejection at CRUD level
* Validation of `use_template` formatting before update
* Ensure forced preset changes cannot be overridden by non-forced without warning

---

_Last updated: August 4, 2025_