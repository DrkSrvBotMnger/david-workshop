# 🛠️ Developer Notes – David's Workshop Bot

This project powers a Discord bot designed for a single fandom server. It tracks event participation, user contributions, and offers a gamified experience through points, titles, badges, and more.

---

## 📦 Stack

- **Language**: Python
- **Discord API**: `discord.py`
- **Data Storage**: SQLite
- **Hosting**: Replit
- **Database**: SQLite

---

## 🧱 File Structure

- /db/           - SQLAlchemy models and DB setup 
- /tests/        - Automated unit tests (planned) 
- /commands/     - Future modular command handlers 
- main.py        - Bot entry point 
- utils.py       - Shared helpers 
- admingroup.py  - Admin/mod commands 
- data.db        - SQLite database (excluded from Git) 
- .gitignore     - Excludes secrets and sensitive data

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
- all db files
- `.env` (Discord bot token and other secrets)

Never commit Discord tokens or private user data.

---

## 👥 Future Collaboration

- Contributors should fork, branch, and test in Replit before PRs
- Consider adding a `CONTRIBUTING.md` later if more people join

Last updated: **2025-07-12**
