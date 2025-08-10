from .dto import UserDTO

def user_to_dto(row) -> UserDTO:
    return UserDTO(
        id=row.id, 
        user_discord_id=row.user_discord_id,
        points=row.points,
        total_earned=row.total_earned,
        total_spent=row.total_spent,
        username=row.username,
        display_name=row.display_name, 
        nickname=row.nickname
    )