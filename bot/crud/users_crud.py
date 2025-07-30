from db.schema import User
from datetime import datetime


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


def action_is_used(session, action_id: int) -> bool:
    """Return True if any UserAction references this action_key."""
    from db.schema import UserAction
    return session.query(UserAction).filter(UserAction.action_id == action_id).first() is not None