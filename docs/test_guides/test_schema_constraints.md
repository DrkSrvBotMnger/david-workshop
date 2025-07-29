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

## ⚠️ Limitations

It is recommand to run those test with PostgreSql as SQLite has limitation
* ON DELETE SET NULL	May not trigger in SQLite unless FK enforcement is enabled
* ON DELETE RESTRICT	Not tested yet (e.g., UserEventData dependencies)
* CASCADE deletes	Not yet validated on inventory or reward tables

---

_Last updated: July 27, 2025_