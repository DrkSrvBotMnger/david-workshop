from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# === TABLE DEFINITIONS ===

# Users linked to Discord accounts.
# Tracks points, profile metadata, and equipped title.
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    points = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)

    username = Column(String)
    display_name = Column(String)
    nickname = Column(String)

    created_at = Column(String)
    modified_at = Column(String, nullable=True)

    def __repr__(self):
        return f"<User {self.discord_id} | points: {self.points}>"


# Events hosted in the community.
# Includes event type, dates, description, and visibility.
class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True)
    name = Column(String)
    type = Column(String)
    description = Column(Text)
    start_date = Column(String)
    end_date = Column(String)

    coordinator_id = Column(String, nullable=True)
    priority = Column(Integer, default=0)
    shop_section_id = Column(String, nullable=True)
    embed_color = Column(Integer, default=0x7289DA)

    created_by = Column(String)
    created_at = Column(String)
    modified_by = Column(String, nullable=True)
    modified_at = Column(String, nullable=True)

    active = Column(Boolean, default=True)
    visible = Column(Boolean, default=True)

    metadata_json = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Event {self.event_id} ({self.name})>"


# Items owned by users: titles, badges, or stackable rewards.
# Can include acquisition source or equipped status.
class Inventory(Base):
    __tablename__ = 'inventory_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    reward_id = Column(String)
    reward_type = Column(String)
    quantity = Column(Integer, default=1)

    acquired_at = Column(String, nullable=True)
    source_event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    equipped = Column(Boolean, default=False)

    user = relationship("User", backref="inventory")
    source_event = relationship("Event", backref="awarded_items")


# User-specific data for a given event.
# Tracks event participation stats and optional contact info.
class UserEventData(Base):
    __tablename__ = 'user_event_data'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    event_id = Column(Integer, ForeignKey('events.id'))

    points_earned = Column(Integer, default=0)
    joined_at = Column(String)

    ao3_handle = Column(String, nullable=True)
    tumblr_handle = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    last_active_at = Column(String, nullable=True)
    custom_notes = Column(Text, nullable=True)
    status = Column(String, default="active")

    user = relationship("User", backref="event_data")
    event = relationship("Event", backref="participants")
    
    created_by = Column(String)    
    modified_by = Column(String, nullable=True)
    modified_at = Column(String, nullable=True)

# Defines possible actions users or moderators can perform.
# Input expectations are handled in bot logic, not enforced by schema.
class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True)
    action_key = Column(String, unique=True)  # e.g. "submit_fic", "comment_fics"
    description = Column(Text)
    default_self_reportable = Column(Boolean, default=True)

    input_fields_json = Column(Text, nullable=True)  # Optional: expected fields (["url"], etc.)

    created_at = Column(String)

    def __repr__(self):
        return f"<Action {self.action_key}>"


# Configures a specific action's rewards and permissions within a specific event.
# Includes user guidance text to explain how to report the action in this event.
class ActionEventConfig(Base):
    __tablename__ = 'action_event_configs'

    id = Column(Integer, primary_key=True)
    action_id = Column(Integer, ForeignKey('actions.id'))
    event_id = Column(Integer, ForeignKey('events.id'))

    points_granted = Column(Integer, default=0)
    reward_granted = Column(String, nullable=True)
    self_reportable = Column(Boolean, nullable=True)  # If None, use action default

    input_help_text = Column(Text, nullable=True)  # ✅ Per-event user guidance for input

    action = relationship("Action", backref="event_configs")
    event = relationship("Event", backref="action_configs")

    created_by = Column(String)   
    created_at = Column(String) 

# Logs individual actions performed by users.
# Flexible standardized fields enable reporting and filtering.
class UserAction(Base):
    __tablename__ = 'user_actions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action_id = Column(Integer, ForeignKey('actions.id'))
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)

    created_by = Column(String)    
    timestamp = Column(String)  

    url = Column(String, nullable=True)
    numeric_value = Column(Integer, nullable=True)
    text_value = Column(String, nullable=True)
    boolean_value = Column(Boolean, nullable=True)
    date_value = Column(String, nullable=True)

    metadata_json = Column(Text, nullable=True)  # Optional extras

    user = relationship("User", backref="actions")
    action = relationship("Action", backref="performed_by")
    event = relationship("Event", backref="action_logs")
    
