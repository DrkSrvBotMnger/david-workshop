from dataclasses import dataclass

@dataclass(frozen=True)
class UserDTO:
    id: int
    user_discord_id: str
    points: int
    total_earned: int
    total_spent: int
    username: str | None
    display_name: str | None
    nickname: str | None