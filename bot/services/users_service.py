from sqlalchemy.orm import Session
from bot.crud.users_crud import get_or_create_user, get_user_by_discord_id
from bot.domain.mapping import user_to_dto
from bot.domain.dto import UserDTO

def get_or_create_user_dto(session: Session, member) -> UserDTO:
    user = get_or_create_user(session, member)       # CRUD does all writes
    return user_to_dto(user)                          # service maps to DTO

def get_user_dto_by_discord_id(session: Session, discord_id: str) -> UserDTO | None:
    user = get_user_by_discord_id(session, discord_id)
    return user_to_dto(user) if user else None