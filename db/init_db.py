# db/init_db.py
from sqlalchemy import create_engine
from db.schema import Base

# Use a local SQLite file named data.db
DATABASE_URL = "sqlite:///data.db"

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    Base.metadata.create_all(engine)