from db.schema import Event as EventModel, User as UserModel
from bot.domain.dto import UserDTO, EventDTO 

def user_to_dto(u: UserModel) -> UserDTO:
    return UserDTO(
        id=u.id, 
        user_discord_id=u.user_discord_id,
        points=u.points,
        total_earned=u.total_earned,
        total_spent=u.total_spent,
        username=u.username,
        display_name=u.display_name, 
        nickname=u.nickname,
    )

def event_to_dto(ev: EventModel) -> EventDTO:
    return EventDTO(
        id=ev.id,
        event_key=ev.event_key,
        event_name=ev.event_name,
        event_type=ev.event_type,
        event_description=ev.event_description,
        start_date=ev.start_date,
        end_date=ev.end_date,
        coordinator_discord_id=ev.coordinator_discord_id,
        priority=ev.priority or 0,
        tags=ev.tags,
        embed_channel_discord_id=ev.embed_channel_discord_id,
        embed_message_discord_id=ev.embed_message_discord_id,
        role_discord_id=ev.role_discord_id,
        event_status=ev.event_status.value,
    )