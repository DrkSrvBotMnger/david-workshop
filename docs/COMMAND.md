# 📜 COMMANDS.md – Slash Command Reference

## 👑 Admin Commands (`/admin`)

### `/admin createevent`
> Create a new event.
* **Params:** `shortcode`, `name`, `description`, `start_date`
* **Optional:** `end_date`, `coordinator`, `tags`, `embed_channel`, `embed_message_id`, `role_id`, `priority`, `shop_section_id`

### `/admin editevent`
> Edit existing event (non-active only).
* **Params:** `event_id`*
* **Optional:** `name`, `description`, `start_date`, `end_date`, `coordinator`, `tags`, `embed_channel`, `embed_message_id`, `role_id`, `priority`, `shop_section_id`, `reason`

### `/admin deleteevent`
> Delete a non-active and non-visible event.
* **Params:** `shortcode`, `reason`

### `/admin displayevent`
> Make event public (visible) if embed_message_id set.
* **Params:** `shortcode`

### `/admin activateevent`
> Set event as active (and as visible if not already) if embed_message_id set.
* **Params:** `shortcode`

### `/admin deactivateevent`
> Set event as inactive.
* **Params:** `shortcode`

### `/admin hideevent`
> Set event as invisible.
* **Params:** `shortcode`

### `/admin listevents`
> Show all events.
* **Filters:** tag, mod name, active, visible

### `/admin showevent`
> Show all data on a specific event.
* **Params:** event_id

### `/admin eventlog`
> View logs of event actions.
* **Filters:** action type, moderator

## 🧾 User Commands

*(to be expanded)*

* `/profile`
* `/eventlist`
* `/eventmenu`
* `/shop`
* `/inventory`
* `/useitem`
* `/givepoints`
* `/signupevent`

---

> Feel free to expand this with reward/shop commands, action tracking, and custom utilities.

---

_Last updated: July 25, 2025_