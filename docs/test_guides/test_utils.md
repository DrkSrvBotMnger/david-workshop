# 🧪 Test Guide – Utilities & Shared Functions

This guide outlines test coverage for utility functions, access rights helpers, and UI interaction helpers found in `bot/utils.py`.

---

## 📁 **Core Utilities** – File: `tests/utils/test_utils.py`

| Function                     | Covered ✓ | Notes                                                |
| ---------------------------- | --------- | ---------------------------------------------------- |
| `safe_parse_date()`          | ✅         | Multiple formats + invalid cases (parametrized)      |
| `format_discord_timestamp()` | ✅         | Valid + invalid cases (parametrized)                 |
| `format_log_entry()`         | ✅         | Correct formatting, includes action, user, timestamp |

### 🔹 `safe_parse_date(date_str)`

* Accepts formats:

  * `2025-01-01`
  * `2025/01/01`
  * `01/01/2025`
* Invalid formats return `None`

### 🔹 `format_discord_timestamp(iso_str)`

* Valid ISO → `<t:unix:F>` format
* Invalid → returned unchanged

### 🔹 `format_log_entry(...)`

* Includes action, user mention, timestamp
* Supports optional `label` and `description`

---

## 📁 **Access Rights** – File: `tests/utils/test_role_check.py`

| Function               | Covered ✓ | Notes                                   |
| ---------------------- | --------- | --------------------------------------- |
| `is_admin_or_mod()`    | ✅         | Admin, mod-role, and regular-user cases |
| `admin_or_mod_check()` | ⚪ Planned | Check object creation only              |

### 🔹 `is_admin_or_mod(interaction)`

* Returns `False` for no admin/mod rights
* Returns `True` for:

  * Guild admin
  * Member with `MOD_ROLE_IDS` role

---

## 📁 **UI & Interaction Helpers** – File: `tests/utils/test_utils_extended.py`

| Function                      | Covered ✓ | Notes                                             |
| ----------------------------- | --------- | ------------------------------------------------- |
| `now_iso()`                   | ✅         | ISO 8601 string                                   |
| `now_unix()`                  | ✅         | Unix timestamp integer                            |
| `parse_message_link()`        | ✅         | Valid + invalid formats                           |
| `admin_or_mod_check()`        | ✅         | Returns callable check wrapper                    |
| `ConfirmActionView`           | ✅         | Confirm, cancel, and timeout handling             |
| `confirm_action()`            | ✅         | Returns `True`/`False` based on confirm state     |
| `EmbedPaginator` navigation   | ✅         | First, prev, next, last page changes              |
| `paginate_embeds()`           | ✅         | No embeds, single embed, multi-embed              |
| `post_announcement_message()` | ✅         | Valid send, role mention, invalid/exception cases |

---

## 📌 **Potential Additions**

* Integration-style check for `admin_or_mod_check()` on a dummy command
* UI flow integration for `ConfirmActionView` in a real Discord context
* Parametrized paginator navigation tests to cover arbitrary start/end states

---

If you’re good with this, I can move on to **reward commands tests** next, following the same thorough approach we used for CRUD and utils.

Do you want me to proceed with that now?

---

_Last updated: August 4, 2025_