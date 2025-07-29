# 🧪 Test Guide – Shared and Utilities functions Tests

This guide outlines test coverage for utility functions and UI helpers found in `bot/utils.py`.

---

## 📁 Shared utilities - File: `tests/utils/test_utils.py`

### 🔍 Covered Functions

| Function                         | Tested ✓ | Notes                                          |
|----------------------------------|----------|------------------------------------------------|
| `safe_parse_date()`              | ✅       | Accepts multiple formats, rejects invalid ones |
| `format_discord_timestamp()`     | ✅       | Converts ISO to Discord timestamp or fallback  |
| `format_log_entry()`             | ✅       | Generates audit log display strings            |
| `EmbedPaginator.update_footer()` | ✅       | Verifies correct footer per page               |

### 🔹 `safe_parse_date(date_str)`
- Invalid strings return `None` 🔹 basic
- Accepts format `2025-01-01`, `2025/01/01`, `01/01/2025` 

### 🔹 `format_discord_timestamp(iso_str)`
- Valid ISO input → Discord timestamp 🔹 basic
- Invalid input → returned unchanged

### 🔹 `format_log_entry(action, user, timestamp, ...)` 🔹 basic
- Output includes action, user, timestamp
- Output is formated
- Supports optional `label` and `description`

### 🔹 `EmbedPaginator.update_footer()`
- Asserts all embeds include correct page numbers

---

## 📁 Authorization - File: `tests/utils/test_role_check.py`

#### 🔹 Covered Tests 🔹 basic

* [x] `is_admin_or_mod()` returns `False` for non-privileged user (logic test only)
* [x] Positive logic test (admin = True)
* [x] Positive logic test (mod role = True)

#### ⏳ Potential Additions

* [ ] Actual decorator behavior via registered command (if integration testing possible)

---

## 🔧 Next Steps

- Consider mocking `Interaction` to test `paginate_embeds()` routing
- Test view states (e.g. button disable logic) if bugs appear

---

_Last updated: July 27, 2025_