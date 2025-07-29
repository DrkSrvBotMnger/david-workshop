from db.schema import User
from db.schema import Event
from db.schema import EventLog  # Needed for log_event_change()
from datetime import datetime
from sqlalchemy import or_


## Internal functions

# Log function
def log_event_change(*,session, event_id, action, performed_by, description=None):
    log_entry = EventLog(
        event_id=event_id,
        action=action,
        performed_by=performed_by,
        timestamp=str(datetime.utcnow()),
        description=description
    )
    session.add(log_entry)


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
    type,
    description,
    start_date,
    created_by,
    end_date=None,
    coordinator_id=None,
    priority=0,
    shop_section_id=None,
    active=False,
    visible=False,
    tags=None,
    embed_channel_id=None,
    embed_message_id=None,
    role_id=None
):
    event = Event(
        event_id=event_id,
        name=name,
        type=type,
        description=description,
        start_date=start_date,
        end_date=end_date,
        created_by=created_by,
        created_at=str(datetime.utcnow()),
        modified_by=None,
        modified_at=None,
        active=active,
        visible=visible,
        coordinator_id=coordinator_id,
        priority=priority,
        shop_section_id=shop_section_id,
        tags=tags,
        embed_channel_id=embed_channel_id,
        embed_message_id=embed_message_id,
        role_id=role_id
    )

    session.add(event)
    session.flush()  # Ensure event.id is generated
    
    # Log event creation
    log_event_change(
        session=session,
        event_id=event.id,
        action="create",
        performed_by=created_by,
        description=f"Event {name}({event_id}) created."
    )

    return event


# Edit event and log the change
def update_event(
    session, 
    event_id, 
    modified_by,
    modified_at,
    reason=None, 
    **kwargs
):
    event = session.query(Event).filter_by(event_id=event_id).first()
    if not event:
        return None
    event.modified_by = modified_by
    event.modified_at = modified_at
    
    for key, value in kwargs.items():
        if hasattr(event, key):
            setattr(event, key, value)

    log_description = f"Event {event.name} ({event.event_id}) updated."
    if reason:
        log_description += f" Reason: {reason}"

    log_event_change(
        session=session,
        event_id=event.id,
        action="edit",
        performed_by=modified_by,
        description=log_description
    )

    return event


# Delete event and log the deletion
def delete_event(
    session, 
    event_id, 
    deleted_by,
    reason
):
    event = session.query(Event).filter_by(event_id=event_id).first()
    if not event:
        return False
    session.delete(event)

    log_description = f"Event {event.name}({event.event_id}) deleted. Reason: {reason}"
    
    # Log event deletion
    log_event_change(
        session=session, 
        event_id=event.id, 
        action="delete", 
        performed_by=deleted_by, 
        description=log_description
    )
    
    return True


def get_all_events(session, tag: str = None, active: bool = None, visible: bool = None, mod_id: str = None):
    query = session.query(Event)

    if tag:
        query = query.filter(Event.tags.ilike(f"%{tag}%"))
    if active is not None:
        query = query.filter(Event.active == active)
    if visible is not None:
        query = query.filter(Event.visible == visible)
    if mod_id:
        query = query.filter(or_(Event.created_by == mod_id, Event.modified_by == mod_id))

    return query.order_by(Event.created_at.desc()).all()


def get_all_event_logs(session, action: str = None, moderator: str = None):
    query = session.query(EventLog, Event.event_id).outerjoin(Event, EventLog.event_id == Event.id)

    if action:
        query = query.filter(EventLog.action == action)
    if moderator:
        query = query.filter(EventLog.performed_by == moderator)

    return query.order_by(EventLog.timestamp.desc()).all()
