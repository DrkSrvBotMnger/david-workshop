# 🧪 TEST_README.md

A guide for writing, running, and organizing tests in the David Workshop project.

---

## ✅ Marker System

We use **two types of markers** with `pytest` to categorize and prioritize tests:

### 📂 Category Markers (by feature)

Use these to target specific parts of the system:

* `@pytest.mark.schema` – database-level constraints
* `@pytest.mark.crud` – direct DB access logic
* `@pytest.mark.admin` – slash commands for admins/mods
* `@pytest.mark.user` – slash commands for regular members
* `@pytest.mark.utils` – helpers and shared functions

### ⚡ Workflow Markers (by speed/importance)

* `@pytest.mark.basic` – fast tests for CI or pre-commit runs

You can combine them freely.

---

## 🧪 Running Tests

### 🔹 Common Test Commands

| What to Run               | Command                           |
| ------------------------- | --------------------------------- |
| Only schema tests         | `pytest -m schema`                |
| Only admin command tests  | `pytest -m admin`                 |
| All basic tests           | `pytest -m basic`                 |
| Basic + utils only        | `pytest -m "utils and basic"`     |
| All non-basic admin tests | `pytest -m "admin and not basic"` |
| All except utils          | `pytest -m "not utils"`           |

> ✅ **Tip:** Don't use escape quotes. `pytest -m "admin and basic"` is correct.

### 🔹 Useful Pytest Flags

| Flag                 | Purpose                                |
| -------------------- | -------------------------------------- |
| `-v`                 | Verbose output (test names + status)   |
| `-x`                 | Stop after first failure               |
| `--maxfail=2`        | Stop after 2 failures                  |
| `-k "name"`          | Run tests that match substring in name |
| `--tb=short`         | Short traceback format                 |
| `--disable-warnings` | Suppress warnings in output            |


### 🔹 Run All Tests (default)

```bash
pytest -v
```

---

## 🔧 Test Setup & Cleanup Tips

### ✅ Use the test database

Set `DB_MODE=test` to use the testing schema, and define `DATABASE_URL_TEST` in `.env`.

```env
DB_MODE=test
DATABASE_URL_TEST=postgresql://.../your_test_db
```

### ✅ Fixture for clean DB session

```python
# Automatically set up and tear down the schema once per session
@pytest.fixture(scope="session", autouse=True)
def initialize_test_db():
    engine = create_engine(os.environ["DATABASE_URL_TEST"], echo=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

# Provide a clean DB session per test
@pytest.fixture(scope="function")
def test_session():
    engine = create_engine(os.environ["DATABASE_URL_TEST"], echo=True)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()
```

### 🚫 Avoid dirty state

* Always roll back or drop after each test
* Don’t rely on previously seeded objects unless done via fixture

### ✅ Seed helper example

```python
@pytest.fixture
def seed_user_and_event():
    def _seed(session):
        bot.crud.get_or_create_user(session, "1234", "TestUser")
        return bot.crud.create_event(...)
    return _seed
```

### 🔪 Full test file example

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock
from bot.crud import get_or_create_user

@pytest.mark.utils
@pytest.mark.basic
def test_get_or_create_user_creates(test_session):
    # Ensure user doesn't exist
    user = get_or_create_user(test_session, "9999", "ExampleUser")
    assert user.discord_id == "9999"
    assert user.username == "ExampleUser"

@pytest.mark.utils
@pytest.mark.basic
def test_get_or_create_user_returns_existing(test_session):
    # Seed user first
    get_or_create_user(test_session, "9999", "ExampleUser")
    user_again = get_or_create_user(test_session, "9999", "ShouldBeIgnored")
    assert user_again.discord_id == "9999"
    assert user_again.username == "ExampleUser"
```

---

## 📁 Directory Structure

```
tests/
├── admin/
│   ├── test_create_event.py
│   ├── test_edit_event.py
│   ├── test_delete_event.py
│   └── ...
├── crud/
│   ├── test_events.py
│   ├── test_users.py
│   └── ...
├── schema/
│   ├── test_constraints_events.py
│   └── ...
├── user/
│   ├── test_profile.py
│   └── ...
├── utils/
│   ├── test_role_check.py
│   └── ...
└── conftest.py
```

---

## 📌 Best Practices

* Use `async def` with `@pytest.mark.asyncio` for bot commands
* Patch external API calls (e.g. `discord`, `datetime`) using `unittest.mock`
* Use `MagicMock` for interaction mocks, and patch `crud` for internal logic
* Keep test files < 300 lines; split by command or feature if needed

---

For questions or to add new markers, ping the project maintainer or update `pytest.ini`.
Happy testing! 🧪
