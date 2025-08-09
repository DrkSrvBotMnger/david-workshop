import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

mode = os.getenv("DB_MODE", "dev").lower()

if mode in ("test",):
    DATABASE_URL = os.getenv("DATABASE_URL_TEST")
elif mode in ("qa", "staging"):
    DATABASE_URL = os.getenv("DATABASE_URL_QA")
elif mode in ("prod", "production"):
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    DATABASE_URL = os.getenv("DATABASE_URL_DEV")
    
print(mode)

if not DATABASE_URL:
    raise RuntimeError(
        "❌ No DATABASE_URL found. Set DB_MODE to 'test', 'dev', or 'prod' and define the corresponding environment variable."
    )

# Create engine + session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        print(f"❌ DB error: {e}")
        session.rollback()
        raise
    finally:
        session.close()
