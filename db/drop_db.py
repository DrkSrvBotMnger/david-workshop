import os
from database import engine
from schema import Base
from sqlalchemy import text

mode = os.getenv("DB_MODE", "dev").lower()

confirm = input(f"⚠️ You are about to DROP ALL TABLES in the *{mode}* database. Are you sure? (yes/no): ")
if confirm.lower() != "yes":
    print("✅ Operation cancelled.")
    exit()

print("Dropping ALL tables...")
Base.metadata.drop_all(bind=engine)
print(f"🧨 Dropped schema for DB_MODE={mode}.")