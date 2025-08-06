# 🧪 Actions Command Test Guide

This guide covers **what we test**, **how we test it**, and **key mocking tips** for all `/admin_action` commands.

---

## **1️⃣ Test Structure**

* Tests are **grouped by command**:

  * `create` / `delete` / `deactivate` / `list` are all in the same test file.
* **Shared fixtures**:

  * `mock_interaction` (AsyncMock for `.response.defer`, `.followup.send`, `.edit_original_response`)
  * `invoke_app_command` helper in `tests/helpers.py`
* **Patch all DB writes** in tests — no real DB writes occur.

---

## **2️⃣ Commands & Test Coverage**

### **`/admin_action create`**

* ✅ Creates successfully with valid key and description.
* ❌ Fails if key invalid.
* ❌ Fails if action already exists.

**Mocking tips**:

* Patch:

  * `actions_crud.get_action_by_key`
  * `actions_crud.create_action`
* Keep `input_fields` optional in tests.

---

### **`/admin_action delete`**

* ✅ Deletes successfully if active and unused.
* ❌ Fails if action not found.
* ❌ Fails if action is in use.
* ❌ Fails if action inactive.

**Mocking tips**:

* Patch:

  * `actions_crud.get_action_by_key`
  * `actions_crud.delete_action` (or let DB delete pass silently)
  * `action_is_used`
* Use `fake_action.is_active = True/False` to simulate status.

---

### **`/admin_action deactivate`**

* ✅ Success → marks inactive and versions key.
* ❌ Not found.
* ❌ Already inactive.

**Mocking tips**:

* Patch:

  * `actions_crud.get_action_by_key`
  * `actions_crud.deactivate_action` or `update_action` depending on implementation.
* Use a fake action with `.is_active = True` for success case.
* Ensure while-loop for versioning doesn't hang by returning `None` after first candidate check.

---

### **`/admin_action list`**

* ✅ No actions found → "ℹ️ No actions found with the current filters."
* ✅ Actions exist → calls `paginate_embeds`.

**Mocking tips**:

* Patch:

  * `actions_crud.get_all_actions`
  * `paginate_embeds` (AsyncMock)
* Use fake action objects with relevant `.input_fields_json` and `.is_active`.

---

## **3️⃣ General Mocking Rules**

1. **Always mock DB calls** in CRUD to avoid real queries.
2. **Always mock Discord API calls** (`send`, `delete`, `fetch_channel`) to AsyncMocks.
3. Keep fake object state realistic (

   ```python
   fake_action.is_active = True
   fake_action.action_key = "myaction"
   ```

   ).
4. When testing deactivate versioning, patch `get_action_by_key` to return:

   * Fake action on first call (current key)
   * `None` on second call (new version key available)

---

## **4️⃣ Future Improvements**

* Add embed structure validation for `/list` to ensure correct field formatting.
* Add input field parsing/validation tests for `/create`.

---

_Last updated: August 5, 2025_