# 🧪 Rewards Command Test Guide

This guide covers **what we test**, **how we test it**, and **key mocking tips** for all `/admin_reward` commands.

---

## **1️⃣ Test Structure**

* Tests are **grouped by command**:

  * `create` → `test_reward_create.py`
  * `edit` → `test_reward_edit.py`
  * `delete` → `test_reward_delete.py`
  * `list + show + logs` → `test_reward_list_show_logs.py`
  * `publishpreset` → `test_reward_publish_preset.py`

* **Shared fixtures**:

  * `mock_interaction` (AsyncMock for `.response.defer`, `.followup.send`, `.edit_original_response`)
  * `invoke_app_command` helper in `tests/helpers.py`

* **Patch all DB writes** in tests — no real DB writes occur.
* **Patch Discord fetch/send/delete** calls to avoid real API calls.

---

## **2️⃣ Commands & Test Coverage**

### **`/admin_reward create`**

* ✅ Creates reward successfully
* ❌ Fails if badge without emoji
* ✅ Removes emoji for non-badge
* ✅ Forces `is_stackable=False` for non-stackable types
* ❌ Fails if already exists

**Mocking tips**:

* Patch:
  * `rewards_crud.get_reward_by_key`
  * `rewards_crud.create_reward`
* Assert that the passed `reward_create_data` matches expected values.

---

### **`/admin_reward edit`**

* ✅ Edits successfully
* ❌ Reward not found
* ❌ Linked to active event without `force` → blocked
* ✅ Linked to active event with `force` → allowed
* ❌ Badge without valid emoji → blocked
* ❌ No valid fields → blocked (after fixing stackable default)

**Mocking tips**:

* Patch:
  * `rewards_crud.get_reward_by_key`
  * `rewards_crud.update_reward`
  * `rewards_crud.reward_is_linked_to_active_event`
  * `confirm_action` (AsyncMock returning True/False)

---

### **`/admin_reward delete`**

* ✅ Success delete after confirm
* ❌ Reward not found
* ❌ Cancelled by user
* **To add later**: Linked to active event without force / with force

**Mocking tips**:

* Patch:
  * `rewards_crud.get_reward_by_key`
  * `rewards_crud.delete_reward`
  * `confirm_action` to avoid hanging tests

---

### **`/admin_reward list`**

* ✅ No rewards → sends `"❌ No rewards found."`
* ✅ Rewards exist → calls `paginate_embeds`

**Mocking tips**:

* Patch:
  * `rewards_crud.get_all_rewards`
  * `paginate_embeds` (AsyncMock)

---

### **`/admin_reward show`**

* ❌ Reward not found
* ✅ Reward exists → sends correct embed
* ✅ (Improvement) Check embed structure per reward type

**Mocking tips**:

* Patch:
  * `rewards_crud.get_reward_by_key`
* Assert embed type and required fields.

---

### **`/admin_reward logs`**

* ✅ No logs → `"❌ No logs found"`
* ✅ Logs exist → calls `paginate_embeds`

**Mocking tips**:

* Patch:
  * `rewards_crud.get_reward_logs`
  * `paginate_embeds` (AsyncMock)

---

### **`/admin_reward publishpreset`**

* ❌ Reward not found
* ❌ Wrong type (not `preset`)
* ❌ Invalid message link format
* ✅ Success publish (skips old preset archive)
* **To add later**: Linked to active event without force / with force

**Mocking tips**:

* Patch:
  * `rewards_crud.get_reward_by_key`
  * `rewards_crud.reward_is_linked_to_active_event`
  * `rewards_crud.publish_preset`
  * `self.bot.fetch_channel` (AsyncMock → fake channel → fake message with `delete=AsyncMock()`)
  * `guild.get_channel` (returns fake preset channel with `send=AsyncMock()`)

---

## **3️⃣ General Mocking Rules**

1. **Always mock DB calls** in CRUD to avoid real queries.
2. **Always mock Discord API calls** (`fetch_channel`, `fetch_message`, `send`, `delete`) to AsyncMocks.
3. **Always control confirmation prompts** with:

   ```python
   monkeypatch.setattr("bot.commands.admin.rewards_admin.confirm_action", AsyncMock(return_value=True))
   ```
4. Keep test cases **isolated** — don’t reuse patched objects across unrelated tests.

---

## **4️⃣ Future Improvements**

* Add embed structure validation for `/show` by reward type.
* Add linked-to-active-event tests for `/delete` and `/publishpreset`.
* Add tests for archive/delete old preset in `/publishpreset`.
* Use parametrized tests for similar scenarios (reduces duplication).

---

If you want, I can now make a **companion quick-reference table** showing **command → tests → mocks** in one compact view so it’s even easier to maintain.

Do you want me to do that?

---

_Last updated: August 4, 2025_