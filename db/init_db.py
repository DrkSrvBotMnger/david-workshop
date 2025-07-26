import os
from schema import Base
from database import engine

mode = os.getenv("DB_MODE", "dev").lower()

if mode != "test":
    confirm = input(f"❗️You are about to initialize the *{mode}* database schema. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Operation cancelled.")
        exit()

Base.metadata.create_all(engine)
print(f"✅ Initialized schema for DB_MODE={mode}.")
