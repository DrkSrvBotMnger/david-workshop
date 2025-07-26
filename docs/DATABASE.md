# 🗄️ DATABASE.md – Schema Overview

## 🔗 Tables Overview

### `users`

* `id` (PK)
* `discord_id` (unique, Discord user ID)
* `username`, `display_name`, `nickname`
* `points`, `total_earned`, `total_spent` (int)
* `created_at`, `modified_at` (str)

### `events`

* `id` (PK)
* `event_id` (unique)
* `name`, `type`, `description`
* `start_date`, `end_date` (str)
* `visible`, `active` (bool)
* `coordinator_id` (Discord user ID)
* `created_by`, `last_edited_by` (Discord user ID)
* `created_at`, `modified_at` (str)
* `embed_channel_id`, `embed_message_id`, `role_id` (Discord IDs)

### `event_logs`

* `id` (PK)
* `event_id` (FK → events, on delete → set null)
* `action`
* `performed_by` (Discord user ID)
* `timestamp`
* `description`

### \[Planned Tables]

* `rewards`, `event_rewards`
* `actions`, `action_event_config`
* `user_actions`, `user_event_data`

_Last updated: July 25, 2025_