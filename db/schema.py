from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# === TABLE DEFINITIONS ===

# Users linked to Discord accounts.
# Tracks points and profile metadata.
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

    active = Column(Boolean, default=False)
    visible = Column(Boolean, default=False)

    metadata_json = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Event {self.event_id} ({self.name})>"

# Logs changes to events by moderators.
class EventLog(Base):
    __tablename__ = 'event_logs'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    action = Column(String)  # e.g. 'create', 'edit', 'delete'
    performed_by = Column(String)  # Discord ID of the mod/user
    timestamp = Column(String)  # Store as ISO timestamp
    description = Column(Text, nullable=True)  # Optional note or metadata

    event = relationship("Event", backref="change_logs")

    def __repr__(self):
        return f"<EventLog event_id={self.event_id} action={self.action} performed_by={self.performed_by}>"


# Rewards owned by users: titles, badges, or items (stackable or not).
# Can include acquisition source or equipped status.
class Inventory(Base):
    __tablename__ = 'inventory_rewards'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    reward_id = Column(String)
    reward_type = Column(String)
    quantity = Column(Integer, default=1)

    acquired_at = Column(String, nullable=True)
    source_event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    equipped = Column(Boolean, default=False)

    user = relationship("User", backref="inventory")
    source_event = relationship("Event", backref="event_rewards")

    def __repr__(self):
        return f"<Inventory user_id={self.user_id} reward_id='{self.reward_id}' quantity={self.quantity}>"


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

    def __repr__(self):
        return f"<UserEventData user_id={self.user_id} event_id={self.event_id} status='{self.status}'>"


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

    input_help_text = Column(Text, nullable=True)  # Per-event user guidance for input

    action = relationship("Action", backref="event_configs")
    event = relationship("Event", backref="action_configs")

    created_by = Column(String)   
    created_at = Column(String) 

    def __repr__(self):
        return f"<ActionEventConfig action_id={self.action_id} event_id={self.event_id} points={self.points_granted}>"


# Logs individual actions performed by users.
# Flexible standardized fields enable reporting and filtering.
class UserAction(Base):
    __tablename__ = 'user_actions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action_id = Column(Integer, ForeignKey('actions.id'))
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)

    created_by = Column(String)    # for when actions are logged by a mod for out of server participants
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

    def __repr__(self):
        return f"<UserAction user_id={self.user_id} action_id={self.action_id} timestamp={self.timestamp}>"


# Rewards available: titles, badges, or items.
# Shows stackability of items and the number of rewards distributed to users.
class Rewards(Base):
    __tablename__ = 'rewards'

    id = Column(Integer, primary_key=True)
    reward_id = Column(String, unique=True)
    reward_type = Column(String, nullable=False)  # e.g., 'title', 'badge', 'item'
    reward_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    emoji = Column(String, nullable=True)      # For type 'badge'
    media_url = Column(String, nullable=True)  # For type 'item'
    stackable = Column(Boolean, default=False) # Only relevant for type 'item'
    
    number_granted = Column(Integer, default=0)  # Cumulative tracking counter
            
    created_by = Column(String)
    created_at = Column(String)
    
    def __repr__(self):
        return f"<Rewards(reward_id='{self.reward_id}', type='{self.reward_type}', name='{self.reward_name}')>"

# Logs changes to rewards by moderators.
class RewardLog(Base):
    __tablename__ = 'reward_logs'

    id = Column(Integer, primary_key=True)
    reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=True)
    action = Column(String)  # e.g. 'create', 'edit', 'delete'
    performed_by = Column(String)  # Discord ID of the mod/user
    timestamp = Column(String)  # ISO timestamp
    description = Column(Text, nullable=True)  # Optional metadata (reason, changes, etc.)

    reward = relationship("Rewards", backref="change_logs")

    def __repr__(self):
        return f"<RewardLog reward_id={self.reward_id} action={self.action} performed_by={self.performed_by}>"


# Links rewards to events.
# Determines if reward is sold in shop or granted by performing an action.
class EventReward(Base):
    __tablename__ = 'event_rewards'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=False)

    availability = Column(String, nullable=False, default="inshop")  
    # 'inshop' or 'onaction'

    price = Column(Integer, nullable=False, default=0)  
    # Used if availability == 'inshop'

    actionevent_id = Column(Integer, ForeignKey('action_event_configs.id'))  
    # Used if availability == 'onaction'

    def __repr__(self):
        return f"<EventReward(event_id={self.event_id}, reward_id={self.reward_id}, availability={self.availability})>"
