# db/schema.py
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Base class for table models
Base = declarative_base()

# === TABLE DEFINITIONS ===

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    points = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)

    # Discord name metadata
    username = Column(String)
    display_name = Column(String)
    nickname = Column(String)

    equipped_title = Column(String, nullable=True)

    created_at = Column(String)
    updated_at = Column(String)

    def __repr__(self):
        return f"<User {self.discord_id} | points: {self.points}>"


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True)
    name = Column(String)
    type = Column(String)
    description = Column(Text)
    start_date = Column(String)
    end_date = Column(String)

    # Optional searchable config
    coordinator_id = Column(String, nullable=True)
    priority = Column(Integer, default=0)
    shop_section_id = Column(String, nullable=True)
    embed_color = Column(Integer, default=0x7289DA)

    # Metadata
    created_by = Column(String)
    created_at = Column(String)
    modified_by = Column(String, nullable=True)
    modified_at = Column(String, nullable=True)

    # Visibility & control
    active = Column(Boolean, default=True)
    visible = Column(Boolean, default=True)

    # Optional extras (URLs, banners)
    metadata_json = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Event {self.event_id} ({self.name})>"


class InventoryItem(Base):
    __tablename__ = 'inventory_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    reward_id = Column(String)  # Could be title, badge, item, etc.
    reward_type = Column(String)  # "title", "badge", "item"
    quantity = Column(Integer, default=1)  # for stackables

    user = relationship("User", backref="inventory")


class UserEventData(Base):
    __tablename__ = 'user_event_data'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    event_id = Column(Integer, ForeignKey('events.id'))

    points_earned = Column(Integer, default=0)
    badge_id = Column(String, nullable=True)
    joined_at = Column(String)

    # Optional sensitive info (event-specific)
    ao3_handle = Column(String, nullable=True)
    tumblr_handle = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    user = relationship("User", backref="event_data")
    event = relationship("Event", backref="participants")