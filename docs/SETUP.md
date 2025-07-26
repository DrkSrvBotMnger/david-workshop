# 🛠️ SETUP.md – David's Workshop Bot

## 📦 Requirements

* Python 3.11+
* PostgreSQL (via Railway or local instance)
* Discord bot token* 
* Optional: `pytest` for testing
* Optional: `pytest-asyncio` for testing
* Optional: `pre-commit` for code quality hooks

## 📁 Project Structure Overview

```
project_root/
├── bot/
│ ├── commands/
│ │ └── admin.py                            # Admin slash commands
│ ├── config.py                             # Loads ENV secrets
│ ├── crud.py                               # CRUD operations
│ ├── main.py                               # Main bot launcher
│ └── utils.py                              # Helper functions (pagination, etc.)
├── db/
│ ├── database.py                           # Engine/session factory (uses DB_MODE)
│ ├── drop_db.py                            # Drops the DB (with safety check)
│ ├── init_db.py                            # Initializes the DB
│ ├── utils.py                              # Shared schema functions
│ └── schema.py                             # SQLAlchemy models
├── tests/
│ ├── schema/
│ │ └── test_constraints_events.py
│ ├── conftest.py
│ ├── test_utils.py
│ ├── test_admin_events.py
│ ├── test_crud_events.py
│ └── test_crud_events_extended.py
├── docs/
│ ├── SETUP.md
│ ├── DATABASE.md
│ ├── COMMANDS.md
│ ├── test_guides/
│ │ └── setup_crud_events.md
├── .editorconfig                             # Enforces formatting in IDEs
├── .pre-commit-config.yaml                   # Git hooks for tests & formatting
├── pytest.ini                                # Pytest config (warnings, test paths)
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── requirements.txt
```

---

## 🚀 Setup Instructions

### 1. Clone & Install

```bash
git clone https://github.com/DrkSrvBotMnger/david-workshop
cd david-workshop
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file or set secrets in Railway/Replit.
Example:

```
# Required for bot
DISCORD_TOKEN=your_token_here
ENV=dev                                  # (bot behavior) dev or prod

# Database environment
DB_MODE=dev                              # dev, test, or prod

# Database URLs (PostgreSQL)
DATABASE_URL_DEV=postgres://user:pass@host/dev_db
DATABASE_URL_TEST=postgres://user:pass@host/test_db
DATABASE_URL=postgres://user:pass@host/prod_db
```

### 3. Initialize Database

```bash
python db/init_db.py     # Initializes dev database
python db/drop_db.py     # Destroys dev database
```
If using Railway, set secrets from your dashboard.

### 4. Run the Bot

```bash
python -m bot.main
```
Make sure DB_MODE=dev and ENV=dev are set in your .env or Replit secrets.

### 5. (Optional) Run Tests

```bash
pip install pytest, pytest-asyncio
```
For testing, switch `DB_MODE=test` or use the test DB initializer.
```bash
DB_MODE=test pytest -v
```
Test discovery is scoped to the tests/ folder. Use pytest.ini to manage warnings and verbosity.

### 6. (Optional) Enable Pre-Commit Hooks

```bash
pip install pre-commit
pre-commit install
```
This will:
* Run formatting (black)
* Run tests before commits (pytest)
* Prevent trailing whitespace, EOL issues, etc.

### 7. Editor Formatting (Optional but Recommended)

Your project includes .editorconfig. Supported by:
* VS Code (native)
* PyCharm
* Most modern IDEs

It enforces:
* 4-space indentation
* Unix-style line endings
* No trailing whitespace
* Final newline on save

---

_Last updated: July 26, 2025_