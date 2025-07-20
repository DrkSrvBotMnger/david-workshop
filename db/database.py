from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adjust path as needed – using SQLite in local file:
DATABASE_URL = "sqlite:///bot_database.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

# Dependency function (optional, if used in modular code)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
