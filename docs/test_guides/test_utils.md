# 🧪 Test Guide – `utils.py`

This guide outlines test coverage for utility functions and UI helpers found in `bot/utils.py`.

---

## ✅ File: `tests/test_utils.py`

### 🔹 Covered Functions

| Function                         | Tested ✓ | Notes                                          |
|----------------------------------|----------|------------------------------------------------|
| `safe_parse_date()`              | ✅       | Accepts multiple formats, rejects invalid ones |
| `format_discord_timestamp()`     | ✅       | Converts ISO to Discord timestamp or fallback  |
| `format_log_entry()`             | ✅       | Generates audit log display strings            |
| `EmbedPaginator.update_footer()` | ✅       | Verifies correct footer per page               |

---

## 🧪 Test Breakdown

### 🔹 `safe_parse_date(date_str)`
- Accepts format `2025-01-01`, `2025/01/01`, `01/01/2025` 
- Invalid strings return `None`

### 🔹 `format_discord_timestamp(iso_str)`
- Valid ISO input → Discord timestamp
- Invalid input → returned unchanged

### 🔹 `format_log_entry(action, user, timestamp, ...)`
- Output includes action, user, timestamp
- Output is formated
- Supports optional `label` and `description`

### 🔹 `EmbedPaginator.update_footer()`
- Asserts all embeds include correct page numbers

---

## ❌ Not Covered (Optional)

| Utility               | Reason |
|-----------------------|--------|
| `confirm_action()`    | Requires live interaction simulation |
| `ConfirmActionView`   | UI-based test (covered via command flows) |
| `paginate_embeds()`   | Mostly dispatch logic; relies on Discord's view system |

These can be tested later via integration tests or `discord.ext.test`.

---

## 🔧 Next Steps

- Consider mocking `Interaction` to test `paginate_embeds()` routing
- Test view states (e.g. button disable logic) if bugs appear
