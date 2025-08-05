# 🧪 Test Guide – Schema Constraint Tests

This guide outlines test coverage for database schema-level constraints in **all** relevant tables.
These tests ensure your SQLAlchemy models match expectations for **nullability, defaults, unique constraints, and foreign key behaviors**.

---

## 📁 File: `tests/schema/test_constraints_events.py`

### 🔹 Coverage Summary

| Constraint Type  | Covered ✓ | Notes                                           |
| ---------------- | --------- | ----------------------------------------------- |
| `nullable=False` | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `unique=True`    | ✅         | Unique fields and constraints      |
| `default`        | ✅         | Columns with set default values    |

**Required Field Tests**

* `event_key`, `event_name`, `event_type`, `event_description`, `start_date`, `priority`, `event_status`, `created_by` are mandatory
* Forced-null tests for `priority`, `event_status`

**Nullable Field Tests**

* `end_date`, `tags`, `embed_channel_discord_id`, `embed_message_discord_id`, `role_discord_id`, `modified_by`, `modified_at` can be null

**Unique Constraints**

* `event_key` must be unique

**Default Values**

* `priority=0`
* `event_status` defaults to `draft`

---

## 📁 File: `tests/schema/test_constraints_event_logs.py`

### 🔹 Coverage Summary

| Constraint Type     | Covered ✓ | Notes                                                  |
| ------------------- | --------- | ------------------------------------------------------ |
| `nullable=False`    | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `ondelete=SET NULL` | ✅         | Deleting sets id to null        |

**Required Field Tests**

* `log_action`, `performed_by`, `performed_at` required

**Nullable Field Tests**

* `event_id`, `log_description` may be null

**FK Behavior**

* Deleting Event does **not** delete EventLogs, but sets `event_id` to null

---

## 📁 File: `tests/schema/test_constraints_actions.py`

### 🔹 Coverage Summary

| Constraint Type  | Covered ✓ | Notes                                                      |
| ---------------- | --------- | ---------------------------------------------------------- |
| `nullable=False` | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `unique=True`    | ✅         | Unique fields and constraints      |
| `default`        | ✅         | Columns with set default values    | 

**Required Field Tests**

* `action_key`, `is_active`, `action_description`, `created_at` required
* Forced-null tests for `is_active`

**Nullable Field Tests**

* `input_fields_json`, `deactivated_at ` may be null
  
**Unique Constraints**

* `action_key` must be unique

**Default Values**

* `is_active=True`

---

## 📁 File: `tests/schema/test_constraints_action_event.py`

### 🔹 Coverage Summary

| Constraint Type       | Covered ✓ | Notes                                                                                              |
| --------------------- | --------- | -------------------------------------------------------------------------------------------------- |
| `nullable=False` | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `unique=True`    | ✅         | Unique fields and constraints      |
| `default`        | ✅         | Columns with set default values    | 
| `ondelete=CASCADE`| ✅         | Deleting  FK object deletes the line        |
| `ondelete=SET NULL` | ✅         | Deleting FK object sets id to null        |

**Required Field Tests**

* `action_event_key`, `action_id`, `event_id`, `variant`, `points_granted`, `is_allowed_during_visible`, `is_self_reportable`, `created_by`, `created_at` required
* Forced-null tests for `points_granted`, `is_allowed_during_visible`, `is_self_reportable`

**Nullable Field Tests**

* `reward_event_id`, `input_help_text`, `modified_by`, `modified_at` may be null

**Unique Constraints**

* `action_key` must be unique
* (`event_id`, `action_id`, `variant`) combo unique

**Default Values**

* `points_granted=0`
* `is_allowed_during_visible=False`
* `is_self_reportable=True`

**FK Behavior**

* Deleting Action **deletes** ActionEvent
* Deleting Event **deletes** ActionEvent
* Deleting Reward does **not** delete ActionEvent, but sets `reward_event_id` to null

---

## 📁 File: `tests/schema/test_constraints_action_event_logs.py`

### 🔹 Coverage Summary

| Constraint Type     | Covered ✓ | Notes                               |
| ------------------- | --------- | ----------------------------------- |
| `nullable=False`    | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `ondelete=SET NULL` | ✅         | Deleting sets id to null        |

**Required Field Tests**

* `log_action`, `performed_by`, `performed_at` required

**Nullable Field Tests**

* `action_event_id`, `log_description` may be null

**FK Behavior**

* Deleting ActionEvent does **not** delete ActionEventLogs, but sets `action_event_id` to null

---

## 📁 File: `tests/schema/test_constraints_rewards.py`

### 🔹 Coverage Summary

| Constraint Type  | Covered ✓ | Notes                                                                            |
| ---------------- | --------- | -------------------------------------------------------------------------------- |
| `nullable=False` | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `unique=True`    | ✅         | Unique fields and constraints      |
| `default`        | ✅         | Columns with set default values    | 

**Required Field Tests**

* `reward_key`, `reward_type`, `reward_name`, `is_released_on_active`, `is_stackable`, `number_granted`, `created_by`, `created_at` required
* Forced-null tests for `is_released_on_active`, `is_stackable`, `number_granted`

**Nullable Field Tests**

* `reward_description`, `emoji`, `use_channel_discord_id`, `use_message_discord_id`, `use_header_message_discord_id`, `use_template`, `use_allowed_params`, `use_media_mode`, `modified_by`, `modified_at`, `preset_by`, `preset_at` may be null

**Unique Constraints**

* `reward_key` must be unique

**Default Values**

* `is_released_on_active=False`
* `is_stackable=False`
* `number_granted=0`

---

## 📁 File: `tests/schema/test_constraints_reward_logs.py`

### 🔹 Coverage Summary

| Constraint Type     | Covered ✓ | Notes                          |
| ------------------- | --------- | ------------------------------ |
| `nullable=False`    | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `ondelete=SET NULL` | ✅         | Deleting sets id to null        |

**Required Field Tests**

* `log_action`, `performed_by`, `performed_at` required

**Nullable Field Tests**

* `reward_event_id`, `log_description` may be null

**FK Behavior**

* Deleting Reward does **not** delete RewardLogs, but sets `reward_event_id` to null

---

## 📁 File: `tests/schema/test_constraints_reward_event.py`

### 🔹 Coverage Summary

| Constraint Type  | Covered ✓ | Notes                                                                         |
| ---------------- | --------- | ----------------------------------------------------------------------------- |
| `nullable=False` | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `unique=True`    | ✅         | Unique fields and constraints      |
| `default`        | ✅         | Columns with set default values    | 
| `ondelete=CASCADE`| ✅         | Deleting  FK object deletes the line        |

**Required Field Tests**

* `reward_event_key`, `event_id`, `reward_id`, `availability`, `price`, `created_by`, `created_at` required
* Forced-null tests for `availability`, `price`

**Nullable Field Tests**

* `modified_by`, `modified_at` may be null

**Unique Constraints**

* `reward_event_key` must be unique
* (`event_id`, `reward_id`, `availability`) combo unique

**Default Values**

* `availability='inshop'`
* `price=0`

**FK Behavior**

* Deleting Event **deletes** RewardEvent
* Deleting Reward **deletes** RewardEvent
  
---

## 📁 File: `tests/schema/test_constraints_reward_event_logs.py`

### 🔹 Coverage Summary

| Constraint Type     | Covered ✓ | Notes                               |
| ------------------- | --------- | ----------------------------------- |
| `nullable=False`    | ✅         | All required fields tested for `IntegrityError` |
| `nullable=True`  | ✅         | Optional fields accept `None`      |
| `ondelete=SET NULL` | ✅         | Deleting sets id to null        |

**Required Field Tests**

* `log_action`, `performed_by`, `performed_at` required

**Nullable Field Tests**

* `reward_event_id`, `log_description` may be null

**FK Behavior**

* Deleting RewardEvent does **not** delete RewardEventLogs, but sets `reward_event_id` to null

---

## 📌 Notes & Limitations

* No `RESTRICT` delete constraints are tested yet (e.g., `UserEventData` dependencies).
* Tests are designed to work with SQLAlchemy and PostgreSQL. Issues might arise using other ORM or DB.

---

_Last updated: August 4, 2025_