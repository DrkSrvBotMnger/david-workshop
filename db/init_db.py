import os
from database import engine
from schema import Base

mode = os.getenv("DB_MODE", "dev").lower()

confirm = input(f"❗️You are about to initialize the *{mode}* database schema. Continue? (yes/no): ")
if confirm.lower() != "yes":
    print("❌ Operation cancelled.")
    exit()

Base.metadata.create_all(engine)
print(f"✅ Initialized schema for DB_MODE={mode}.")