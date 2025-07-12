# 🛠️ Developer Notes – David's Workshop Bot

This project powers a Discord bot designed for a single fandom server. It tracks event participation, user contributions, and offers a gamified experience through points, titles, badges, and more.

---

## 📦 Stack

- **Language**: Python
- **Discord API**: `discord.py`
- **Data Storage**: JSON (local on Replit)
- **Hosting**: Replit
- **Database**: Planning to migrate to SQLite later

---

## 🧱 File Structure

main.py - Core bot entry + slash commands
utils.py - All shared data access and helper functions
admingroup.py - Admin/mod command group
users.json - User points, titles, badges, items (excluded from Git)
events.json - Event definitions (safe to track)
shop.json - Shop item definitions
reward_log.json - Reward transaction history (excluded from Git)
event_log.json - Admin actions and event changes (excluded from Git)
user_actions.json - User event participation logs (excluded from Git)

---

## 🧰 Developer Guidelines

- Use `discord.Embed` for all rich responses
- Keep logic out of commands when possible (add helpers to `utils.py`)
- Use descriptive names for events and rewards
- Test new features in Replit before committing

---

## 🔐 Security & Privacy

> **Important**: Certain data files are *intentionally excluded* from version control to protect user privacy and Discord data.

Excluded files via `.gitignore`:
- `users.json`
- `reward_log.json`
- `event_log.json`
- `user_actions.json`
- `.env` (Discord bot token and other secrets)

Never commit Discord tokens or private user data.

---

## 👥 Future Collaboration

- Contributors should fork, branch, and test in Replit before PRs
- Consider adding a `CONTRIBUTING.md` later if more people join

Last updated: **2025-07-12**
