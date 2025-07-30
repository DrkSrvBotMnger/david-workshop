# 🧪 Test Guide – Schema Constraint Tests

This guide outlines test coverage for database schema-level constraints in the `Event` table. These tests ensure that your SQLAlchemy models match real-world expectations for nullability, foreign keys, and uniqueness.

---

## 📁 File: `tests/schema/test_constraints_events.py`

### 🔹 Coverage Summary

| Constraint Type     | Covered ✓  | Notes                                          |
|---------------------|------------|------------------------------------------------|
| `nullable=False`    | ✅         | All required fields tested for IntegrityError  |
| `nullable=True`     | ✅         | Optional field accept `None`                   |
| `unique=True`       | ✅         | Duplicate `event_id` fails                     |


### 🔹 Required Field Tests 🔹 basic
- Fields `event_id`, `name`, `type`, `description`, `start_date`, `created_by`, `priority` are mandatory

### 🔹 Nullable Field Tests
- Optional fields accept None: `end_date`, `shop_section_id`, `tags`, `event_id`, `embed_channel_id`, `embed_message_id`, `role_id`

### 🔹 Unique Constraints 🔹 basic
- `event_id` must be unique

---

## 📁 File: `tests/schema/test_constraints_event_logs.py`

### 🔍 Coverage Summary

| Constraint Type     | Covered ✓  | Notes                                          |
|---------------------|------------|------------------------------------------------|
| `nullable=False`    | ✅         | All required fields tested for IntegrityError  |
| `nullable=True`     | ✅         | Optional field accept `None`                   |
| `ondelete=SET NULL` | ✅         | Event deletion clears FK in `EventLog`         |


### 🔹 Required Field Tests Log table 🔹 basic
- Fields `action`, `performed_by`, `timestamp` are mandatory

### 🔹 Nullable Field Tests Log table
- Optional `description` accept None

### 🔹 Foreign Key Behavior Log table 🔹 basic
- On deletion all logs are still present
- `event_id` become Null

---

## 📁 File: `tests/schema/test_constraints_actions.py`

### 🔹 Coverage Summary

| Constraint Type     | Covered ✓  | Notes |
|---------------------|------------|-------|
| `nullable=False`    | ✅         | `action_key`, `description`, `created_at` tested |
| `nullable=True`     | ✅         | `input_fields_json` can be null |
| `unique=True`       | ✅         | `action_key` must be unique |
| `default`       | ✅         | `default_self_reportable` is set to true by default |

### 🔹 Required Field Tests 🔹 basic
- `action_key` is required (NOT NULL)
- `description` is required
- `created_at` is required

### 🔹 Nullable Field Tests
- `input_fields_json` can be `NULL`
- 
### 🔹 Default Values
- `default_self_reportable` is set to true by default

### 🔹 Unique Constraint 🔹 basic
- `action_key` must be unique

---

## ⚠️ Limitations

It is recommand to run those test with PostgreSql as SQLite has limitation
* ON DELETE SET NULL	May not trigger in SQLite unless FK enforcement is enabled
* ON DELETE RESTRICT	Not tested yet (e.g., UserEventData dependencies)
* CASCADE deletes	Not yet validated on inventory or reward tables

---

_Last updated: July 30, 2025_