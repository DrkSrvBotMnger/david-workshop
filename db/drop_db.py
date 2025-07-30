import os
from database import engine
from schema import Base

mode = os.getenv("DB_MODE", "dev").lower()

confirm = input(f"⚠️ You are about to DROP ALL TABLES in the *{mode}* database. Are you sure? (yes/no): ")
if confirm.lower() != "yes":
    print("✅ Operation cancelled.")
    exit()

Base.metadata.drop_all(engine)
print(f"🧨 Dropped schema for DB_MODE={mode}.")