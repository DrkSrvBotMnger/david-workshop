from database import engine
from schema import Base

def initialize_database():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

if __name__ == "__main__":
    initialize_database()
