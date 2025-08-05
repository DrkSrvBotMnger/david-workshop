import enum
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))		

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text, UniqueConstraint  
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

# === TABLE DEFINITIONS ===

# Users linked to Discord accounts.
# Tracks points and profile metadata.
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_discord_id = Column(String, unique=True, nullable=False)		# discord unique user id
    points = Column(Integer, default=0, nullable=False)
    total_earned = Column(Integer, default=0, nullable=False)
    total_spent = Column(Integer, default=0, nullable=False)

    username = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    nickname = Column(String, nullable=True)

    created_at = Column(String, nullable=False)
    modified_at = Column(String, nullable=True)

    inventory_items = relationship("Inventory", back_populates="user", passive_deletes=True)
    event_data = relationship("UserEventData", back_populates="user", passive_deletes=True)
    actions = relationship("UserAction", back_populates="user", passive_deletes=True)

    def __repr__(self):
        return f"<User {self.user_discord_id} name={self.username}>"


# Event statuses
class EventStatus(enum.Enum):
    draft = "draft"        # Not visible, not active
    visible = "visible"    # Public, can join, limited actions
    active = "active"      # Fully running
    archived = "archived"  # Finished

# Events hosted in the community.
# Includes event type, dates, description, and status.
class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    event_key = Column(String, unique=True, nullable=False)		# user friendly code e.g. 'drkwk2508' 
    event_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    event_description = Column(Text, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=True)
    coordinator_discord_id = Column(String, nullable=True)		# discord unique user id
    priority = Column(Integer, nullable=False, default=0)
    tags = Column(String, nullable=True)		# comma-separated for future search
    embed_channel_discord_id = Column(String, nullable=True)		# discord unique channel id
    embed_message_discord_id = Column(String, nullable=True)		# discord unique message id
    role_discord_id = Column(String, nullable=True)		# discord unique role id

    event_status = Column(Enum(EventStatus), default=EventStatus.draft, nullable=False)

    created_by = Column(String, nullable=False)		# discord unique user id
    created_at = Column(String, nullable=False)
    modified_by = Column(String, nullable=True)		# discord unique user id
    modified_at = Column(String, nullable=True)

    action_configs = relationship("ActionEvent", back_populates="event", passive_deletes=True)
    reward_configs = relationship("RewardEvent", back_populates="event", passive_deletes=True)
    event_participants = relationship("UserEventData", back_populates="event")
    action_logs = relationship("UserAction", back_populates="event")
    change_logs = relationship("EventLog", back_populates="event")
    
    def __repr__(self):
        return f"<Event {self.event_key} name={self.event_name}>"


# Logs changes to events by moderators.
class EventLog(Base):

    __tablename__ = 'event_logs'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id', ondelete="SET NULL"), nullable=True)		# id in events table
    log_action = Column(String, nullable=False)		# 'create', 'edit', 'delete'
    performed_by = Column(String, nullable=False)		# discord unique user id
    performed_at = Column(String, nullable=False)
    log_description = Column(Text, nullable=True)		# optional reason/details

    event = relationship("Event", back_populates="change_logs")

    def __repr__(self):
        if self.event and self.event.event_key:
            event_ref = f"event={self.event.event_key}"
        elif self.event_id is not None:
            event_ref = f"event_id={self.event_id}"
        else: 
            event_ref = f"id={self.id}"

        return (
            f"<EventLog {self.log_action} "
            f"{event_ref} "
            f"by={self.performed_by} at={self.performed_at}>"
        )


# Rewards owned by users: titles, badges, or items (stackable or not).
# Can include acquisition source or equipped status.
class Inventory(Base):
    __tablename__ = 'inventory_rewards'

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)		# id in users table
    reward_id = Column(Integer, ForeignKey('rewards.id', ondelete="CASCADE"), nullable=False)		# id in rewards table
    quantity = Column(Integer, default=1, nullable=False)

    is_equipped = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="inventory_items")
    reward = relationship("Reward", back_populates="owned_by")

    __table_args__ = (UniqueConstraint('user_id', 'reward_id', name='uix_user_reward'),)
    
    def __repr__(self):
        return (
            f"<Inventory user={self.user.user_discord_id if self.user else self.user_id} "
            f"reward={self.reward.reward_key if self.reward else self.reward_id} "
            f"quantity={self.quantity}>"
        )


# User-specific data for a given event.
# Tracks event participation stats and optional contact info.
class UserEventData(Base):
    __tablename__ = 'user_event_data'

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)		# id in users table
    event_id = Column(Integer, ForeignKey('events.id', ondelete="RESTRICT"), nullable=False)		# id in events table

    points_earned = Column(Integer, default=0, nullable=False)
    joined_at = Column(String, nullable=False)

    ao3_handle = Column(String, nullable=True)
    tumblr_handle = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    last_active_at = Column(String, nullable=True)
    custom_notes = Column(Text, nullable=True)
    status = Column(String, default="active", nullable=False)

    created_by = Column(String, nullable=False)		# discord unique user id
    modified_by = Column(String, nullable=True)		# discord unique user id
    modified_at = Column(String, nullable=True)

    user = relationship("User", back_populates="event_data")
    event = relationship("Event", back_populates="event_participants")
    
    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='uix_user_event'),)

    def __repr__(self):
        return (
            f"<UserEventData user={self.user.user_discord_id if self.user else self.user_id} "
            f"event={self.event.event_key if self.event else self.event_id}>"
        )


# Defines possible actions users or moderators can perform.
# Input expectations are handled in bot logic, not enforced by schema.
class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True)
    action_key = Column(String, unique=True, nullable=False)		# user friendly code e.g. 'submit_fic', 'comment', 'join'
    is_active = Column(Boolean, default=True, nullable=False)
    action_description = Column(Text, nullable=False)

    input_fields_json = Column(Text, nullable=True)		# expected fields in json (["url"], etc.)

    created_at = Column(String, nullable=False)
    deactivated_at = Column(String, nullable=True)
    
    event_configs = relationship("ActionEvent", back_populates="action", passive_deletes=True)
    performed_actions = relationship("UserAction", back_populates="action")

    def __repr__(self):
        return f"<Action {self.action_key} description={self.action_description}>"


# Configures a specific action's rewards and permissions within a specific event.
# Includes user guidance text to explain how to report the action in this event.
class ActionEvent(Base):
    __tablename__ = 'action_events'

    id = Column(Integer, primary_key=True)
    action_event_key = Column(String, nullable=False, unique=True)		# user friendly code e.g. 'drkwk2508_submit_fic_default'
    action_id = Column(Integer, ForeignKey('actions.id', ondelete="CASCADE"), nullable=False)		# id in actions table
    event_id = Column(Integer, ForeignKey('events.id', ondelete="CASCADE"), nullable=False)		# id in events table
    variant = Column(String, nullable=False)		# code for action_event_key unicity e.g. 'default', 'current'

    points_granted = Column(Integer, default=0, nullable=False)
    reward_event_id = Column(Integer, ForeignKey('reward_events.id', ondelete="SET NULL"), nullable=True)		# id in rewards table
    is_allowed_during_visible = Column(Boolean, nullable=False, default=False)
    is_self_reportable = Column(Boolean, nullable=False, default=True)
    input_help_text = Column(Text, nullable=True)

    created_by = Column(String, nullable=False)		# discord unique user id 
    created_at = Column(String, nullable=False)

    modified_by = Column(String, nullable=True)		# discord unique user id 
    modified_at = Column(String, nullable=True)

    action = relationship("Action", back_populates="event_configs")
    event = relationship("Event", back_populates="action_configs")
    reward_event = relationship("RewardEvent", back_populates="granted_by_actions")
    change_logs = relationship("ActionEventLog", back_populates="action_event")

    __table_args__ = (
    UniqueConstraint('event_id', 'action_id', 'variant', name='uix_event_action_variant'),
    )

    def __repr__(self):
        return (
            f"<ActionEvent action_event={self.action_event_key} "
            f"points={self.points_granted} and/or "
            f"reward={self.reward_event.reward_event_key if self.reward_event else self.reward_event_id}>"
        )


class ActionEventLog(Base):
    __tablename__ = "action_event_logs"

    id = Column(Integer, primary_key=True)
    action_event_id = Column(Integer, ForeignKey('action_events.id', ondelete="SET NULL"), nullable=True)		# id in action_events table
    log_action = Column(String, nullable=False)		# 'create', 'edit', 'delete'
    performed_by = Column(String, nullable=False)		# discord unique user id
    performed_at = Column(String, nullable=False)
    log_description = Column(Text, nullable=True)		# optional reason/details

    action_event = relationship("ActionEvent", back_populates="change_logs")

    def __repr__(self):
        if self.action_event and self.action_event.action_event_key:
            action_event_ref = f"action_event={self.action_event.action_event_key}"
        elif self.action_event_id is not None:
            action_event_ref = f"action_event_id={self.action_event_id}"
        else: 
            action_event_ref = f"id={self.id}"

        return (
            f"<ActionEventLog {self.log_action} "
            f"{action_event_ref} "
            f"by={self.performed_by} at={self.performed_at}>"
        )


# Logs individual actions performed by users.
# Flexible standardized fields enable reporting and filtering.
class UserAction(Base):
    __tablename__ = 'user_actions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)		# id in users table
    action_id = Column(Integer, ForeignKey('actions.id', ondelete="RESTRICT"), nullable=False)		# id in actions table
    event_id = Column(Integer, ForeignKey('events.id', ondelete="RESTRICT"), nullable=True)		# id in events table

    created_by= Column(String, nullable=False)		# for when actions are logged by a mod, discord unique user id 
    created_at = Column(String, nullable=False)

    url = Column(String, nullable=True)
    numeric_value = Column(Integer, nullable=True)
    text_value = Column(String, nullable=True)
    boolean_value = Column(Boolean, nullable=True)
    date_value = Column(String, nullable=True)

    metadata_json = Column(Text, nullable=True)		# optional extras (tbd)

    user = relationship("User", back_populates="actions")
    action = relationship("Action", back_populates="performed_actions")
    event = relationship("Event", back_populates="action_logs")

    def __repr__(self):
        return (
            f"<UserAction user={self.user.user_discord_id if self.user else self.user_id} "
            f"action={self.action.action_key if self.action else self.action_id} "
            f"event={self.event.event_key if self.event else self.event_id} "
            f"at={self.created_at}>"
        )


# Rewards available: titles, badges, preset or dynamic.
# Shows stackability of items and the number of rewards distributed to users.
class Reward(Base):
    __tablename__ = 'rewards'

    id = Column(Integer, primary_key=True)
    reward_key = Column(String, unique=True, nullable=False)		# user friendly code e.g. 'd_hug', 'p_drkwk01'
    reward_type = Column(String, nullable=False)		# 'title', 'badge', 'preset', 'dynamic'
    reward_name = Column(String, nullable=False)
    reward_description = Column(Text, nullable=True)
    is_released_on_active = Column(Boolean, default=False, nullable=False)

    emoji = Column(String, nullable=True)  # For type 'badge'
    
    # Preset usage field
    use_channel_discord_id = Column(String, nullable=True)		# discord unique channel id
    use_message_discord_id = Column(String, nullable=True)		# discord unique message id
    use_header_message_discord_id = Column(String, nullable=True)		# discord unique message id

    # Dynamic usage fields
    use_template = Column(Text, nullable=True)		# '{user} hugs {target}'
    use_allowed_params = Column(String, nullable=True)		# 'target' or 'target,amount'
    use_media_mode = Column(String, nullable=True)		# 'single', 'random', 'embed', None

    is_stackable = Column(Boolean, default=False, nullable=False)
    number_granted = Column(Integer, default=0, nullable=False)

    created_by = Column(String, nullable=False)		# discord unique user id
    created_at = Column(String, nullable=False)
    modified_by = Column(String, nullable=True)		# discord unique user id
    modified_at = Column(String, nullable=True)

    preset_by = Column(String, nullable=True)		# discord unique user id
    preset_at = Column(String, nullable=True)

    owned_by = relationship("Inventory", back_populates="reward", passive_deletes=True)
    media_list = relationship("RewardMedia", back_populates="reward", passive_deletes=True)
    change_logs = relationship("RewardLog", back_populates="reward")
    event_links = relationship("RewardEvent", back_populates="reward", passive_deletes=True)    

    def __repr__(self):
        return f"<Reward {self.reward_key} name={self.reward_name}>"


# Rewards setup for multiple media (images, GIFs) rewards
class RewardMedia(Base):
    __tablename__ = 'reward_medias'

    id = Column(Integer, primary_key=True)
    reward_id = Column(Integer, ForeignKey('rewards.id', ondelete='CASCADE'), nullable=False)		# id in rewards table
    media_url = Column(String, nullable=False)
    created_by = Column(String, nullable=False)		# discord unique user id
    created_at = Column(String, nullable=False)

    reward = relationship("Reward", back_populates="media_list")

    def __repr__(self):
        return f"<RewardMedia reward={self.reward.reward_key if self.reward else self.reward_id} media_url={self.media_url}>"


# Logs changes to rewards by moderators.
class RewardLog(Base):
    __tablename__ = 'reward_logs'

    id = Column(Integer, primary_key=True)
    reward_id = Column(Integer, ForeignKey('rewards.id', ondelete="SET NULL"), nullable=True)		# id in rewards table
    log_action = Column(String, nullable=False)		# 'create', 'edit', 'delete'
    performed_by = Column(String, nullable=False)		# discord unique user id
    performed_at = Column(String, nullable=False)
    log_description = Column(Text, nullable=True)		# optional reason/details

    reward = relationship("Reward", back_populates="change_logs")

    def __repr__(self):
        if self.reward and self.reward.reward_key:
            reward_ref = f"reward={self.reward.reward_key}"
        elif self.reward_id is not None:
            reward_ref = f"reward_id={self.reward_id}"
        else: 
            reward_ref = f"id={self.id}"

        return (f"<RewardLog {self.log_action} {reward_ref}, by={self.performed_by} at={self.performed_at}>")


# Links rewards to events.
# Determines if reward is sold in shop or granted by performing an action.
class RewardEvent(Base):
    __tablename__ = 'reward_events'

    id = Column(Integer, primary_key=True)
    reward_event_key = Column(String, unique=True, nullable=False)		# user friendly code e.g. 'drkwk2508_d_hug_inshop' 
    event_id = Column(Integer, ForeignKey('events.id', ondelete="CASCADE"), nullable=False)		# id in events table
    reward_id = Column(Integer, ForeignKey('rewards.id', ondelete="CASCADE"), nullable=False)		# id in rewards table

    availability = Column(String, nullable=False, default="inshop")		# 'inshop', 'onaction'
    price = Column(Integer, nullable=False, default=0)

    created_by = Column(String, nullable=False)		# discord unique user id
    created_at = Column(String, nullable=False)

    modified_by = Column(String, nullable=True)		# discord unique user id
    modified_at = Column(String, nullable=True)

    event = relationship("Event", back_populates="reward_configs")
    reward = relationship("Reward", back_populates="event_links")
    granted_by_actions = relationship("ActionEvent", back_populates="reward_event")
    change_logs = relationship("RewardEventLog", back_populates="reward_event")

    __table_args__ = (
        UniqueConstraint('event_id', 'reward_id', 'availability', name='uix_event_reward_availability'),
    )

    def __repr__(self):
        return f"<RewardEvent reward_event_key={self.reward_event_key}>"


class RewardEventLog(Base):
    __tablename__ = "reward_event_logs"

    id = Column(Integer, primary_key=True)
    reward_event_id = Column(Integer, ForeignKey('reward_events.id', ondelete="SET NULL"), nullable=True)		# id in reward_events table
    log_action = Column(String, nullable=False)		# 'create', 'edit', 'delete'
    performed_by = Column(String, nullable=False)		# discord unique user id
    performed_at = Column(String, nullable=False)
    log_description = Column(Text, nullable=True)		# optional reason/details

    reward_event = relationship("RewardEvent", back_populates="change_logs")

    def __repr__(self):
        if self.reward_event and self.reward_event.reward_event_key:
            reward_event_ref = f"reward_event={self.reward_event.reward_event_key}"
        elif self.reward_event_id is not None:
            reward_event_ref = f"reward_event_id={self.reward_event_id}"
        else: 
            reward_event_ref = f"id={self.id}"

        return (
            f"<RewardEventLog {self.log_action} "
            f"{reward_event_ref} "
            f"by={self.performed_by} at={self.performed_at}>"
        )