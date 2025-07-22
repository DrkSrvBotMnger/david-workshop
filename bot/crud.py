from db.schema import User
from db.schema import Event
from db.schema import EventLog  # Needed for log_event_change()
from datetime import datetime


## Internal functions

# Log function
def log_event_change(session, event_id, action, performed_by, description=None):
    log_entry = EventLog(
        event_id=event_id,
        action=action,
        performed_by=performed_by,
        timestamp=str(datetime.utcnow()),
        description=description
    )
    session.add(log_entry)
    session.commit()


## User-related operations

# Create or fetch existing user
def get_or_create_user(session, discord_id, username=None):
    user = session.query(User).filter_by(discord_id=discord_id).first()
    if not user:
        user = User(
            discord_id=discord_id,
            username=username,
            created_at=str(datetime.utcnow())
        )
        session.add(user)
        session.commit()
    return user

# Update user profile
def update_user(session, discord_id, display_name=None, nickname=None):
    user = session.query(User).filter_by(discord_id=discord_id).first()
    if not user:
        return None

    if display_name:
        user.display_name = display_name
    if nickname:
        user.nickname = nickname

    user.modified_at = str(datetime.utcnow())
    session.commit()
    return user

# Fetch user profile
def get_user(session, discord_id):
    return session.query(User).filter_by(discord_id=discord_id).first()


## Event-related operations

# Check existing events
def get_event(session, event_id):
    return session.query(Event).filter_by(event_id=event_id).first()

# Create an event and log the creation
def create_event(
    session,
    event_id,
    name,
    type_,
    description,
    start_date,
    end_date,
    created_by,
    coordinator_id=None,
    priority=0,
    shop_section_id=None,
    embed_color=0x7289DA,
    metadata_json=None,
    active=False,
    visible=False
):
    event = Event(
        event_id=event_id,
        name=name,
        type=type_,
        description=description,
        start_date=start_date,
        end_date=end_date,
        created_by=created_by,
        created_at=str(datetime.utcnow()),
        active=False,
        visible=False,
        coordinator_id=coordinator_id,
        priority=priority,
        shop_section_id=shop_section_id,
        embed_color=embed_color,
        metadata_json=metadata_json
    )
    
    session.add(event)
    session.commit()

    # Log event creation
    log_event_change(
        session,
        event.id,
        "create",
        performed_by=created_by,
        description=f"Event '{name}' created."
    )

    return event


# Edit event and log the change
def update_event(session, event_id, modified_by, **kwargs):
    event = session.query(Event).filter_by(event_id=event_id).first()
    if not event:
        return None

    for key, value in kwargs.items():
        if hasattr(event, key):
            setattr(event, key, value)

    session.commit()

    # Log event edit
    log_event_change(session, event.id, "edit", performed_by=modified_by, description=f"Event '{event.name}' updated.")

    return event

# Delete event and log the deletion
def delete_event(session, event_id, deleted_by):
    event = session.query(Event).filter_by(event_id=event_id).first()
    if not event:
        return False

    session.delete(event)
    session.commit()

    # Log event deletion
    log_event_change(session, event.id, "delete", performed_by=deleted_by, description=f"Event '{event.name}' deleted.")

    return True