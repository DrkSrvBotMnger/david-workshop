# 🧪 Events Command Test Guide

This guide covers **what we test**, **how we test it**, and **key mocking tips** for all `/admin_event` commands.

---

## **1️⃣ Test Structure**

* Tests are **grouped by command**:

  * `create` → `test_event_create.py`
  * `edit` → `test_event_edit.py`
  * `delete` → `test_event_delete.py`
  * `list + show + logs` → `test_event_list_show_logs.py`
  * `setstatus` → `test_event_setstatus.py`

* **Shared fixtures**:

  * `mock_interaction` (AsyncMock for `.response.defer`, `.followup.send`, `.edit_original_response`)
  * `invoke_app_command` helper in `tests/helpers.py`

* **Patch all DB writes** in tests — no real DB writes occur.

* **Patch Discord fetch/send/delete** calls to avoid real API calls.

---

## **2️⃣ Commands & Test Coverage**

### **`/admin_event create`**

* ✅ Creates event successfully
* ✅ Creates with coordinator specified (doesn’t default to current user)
* ❌ Fails if event already exists
* ❌ Fails if description missing

**Mocking tips**:

* Patch:

  * `events_crud.get_event_by_key`
  * `events_crud.create_event`
* If testing coordinator argument, use a fake object with `.id`.

---

### **`/admin_event edit`**

* ✅ Edits successfully (update name, description, etc.)
* ❌ Event not found
* ❌ No valid fields → blocked
* ✅ Linked to active event with `force` → allowed
* ❌ Linked to active event without `force` → blocked

**Mocking tips**:

* Patch:

  * `events_crud.get_event_by_key`
  * `events_crud.update_event`
  * `events_crud.event_is_linked_to_active_event`
  * `confirm_action` (AsyncMock returning True/False)
* Mutate the **same fake event object** in `update_event` so the updated name is visible in success message.

---

### **`/admin_event delete`**

* ✅ Success delete after confirm
* ❌ Event not found
* ❌ Cancelled by user
* ❌ Missing reason
* **To add later**: Linked to active event without force / with force

**Mocking tips**:

* Patch:

  * `events_crud.get_event_by_key`
  * `events_crud.delete_event`
  * `confirm_action` to avoid hanging tests
* Use `mock_interaction.edit_original_response.assert_awaited_with(...)` for final confirmation messages.

---

### **`/admin_event list`**

* ✅ No events → sends `"❌ No events found."`
* ✅ Events exist → calls `paginate_embeds`

**Mocking tips**:

* Patch:

  * `events_crud.get_all_events`
  * `paginate_embeds` (AsyncMock)

---

### **`/admin_event show`**

* ❌ Event not found
* ✅ Event exists → sends correct embed
* ✅ (Improvement) Check embed structure for expected fields

**Mocking tips**:

* Patch:

  * `events_crud.get_event_by_key`
* Assert embed type and required fields.

---

### **`/admin_event logs`**

* ✅ No logs → `"❌ No logs found for this event."`
* ✅ Logs exist → calls `paginate_embeds`

**Mocking tips**:

* Patch:

  * `events_crud.get_event_logs`
  * `paginate_embeds` (AsyncMock)

---

### **`/admin_event setstatus`**

* ✅ Success update → announcement optional
* ❌ Event not found
* ❌ Invalid transition
* ❌ Missing embed when making visible
* ✅ Posts announcement when becoming visible/active with embed

**Mocking tips**:

* Patch:

  * `events_crud.get_event_by_key`
  * `events_crud.set_event_status` → return **fake\_event**, not `True`
  * `post_announcement_message` (AsyncMock)
* Use `FakeChoice` helper for `event_status` arg to simulate `app_commands.Choice[str]`.
* Give `fake_event.id` a real integer so DB logging doesn’t fail.

---

## **3️⃣ General Mocking Rules**

1. **Always mock DB calls** in CRUD to avoid real queries.
2. **Always mock Discord API calls** (`fetch_channel`, `fetch_message`, `send`, `delete`) to AsyncMocks.
3. **Always control confirmation prompts** with:

   ```python
   monkeypatch.setattr(
       "bot.commands.admin.events_admin.confirm_action",
       AsyncMock(return_value=True)
   )
   ```
4. Keep test cases **isolated** — don’t reuse patched objects across unrelated tests.
5. Return **the same fake event object** from `get_event_by_key` and `set_event_status` to keep state consistent.

---

## **4️⃣ Future Improvements**

* Add embed structure validation for `/show` by event type/status.
* Add linked-to-active-event tests for `/delete` and `/setstatus`.

---

_Last updated: August 5, 2025_