from db.database import engine
from db.schema import Base

def drop_all():
    print("⚠️ Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tables dropped.")

if __name__ == "__main__":
    drop_all()