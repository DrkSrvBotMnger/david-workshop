# Run with DB_MODE=test for CI-safe usage.
# Example: DB_MODE=test python db/init_db.py

import os
from schema import Base
from database import engine

mode = os.getenv("DB_MODE", "dev").lower()

if mode != "test":
    confirm = input(f"⚠️ You are about to DROP ALL TABLES in the *{mode}* database. Are you sure? (yes/no): ")
    if confirm.lower() != "yes":
        print("✅ Operation cancelled.")
        exit()

Base.metadata.drop_all(engine)
print(f"🧨 Dropped schema for DB_MODE={mode}.")
