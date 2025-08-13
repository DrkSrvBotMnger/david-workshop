# bot/services/prompts_service.py
from dataclasses import dataclass

# --- Users DTOs ---

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

# --- Events DTOs ---

@dataclass(frozen=True)
class EventDTO:
    id: int
    event_key: str
    event_name: str
    event_type: str
    event_description: str
    start_date: str
    end_date: str | None
    coordinator_discord_id : str | None
    priority: int
    tags: str | None
    embed_channel_discord_id: str | None
    embed_message_discord_id: str | None
    role_discord_id: str | None
    event_status: str

@dataclass(frozen=True)
class EventMessageRefsDTO:
    event_key: str
    event_name: str
    embed_channel_discord_id: str
    embed_message_discord_id: str

# --- Rewards DTOs ---

@dataclass(frozen=True)
class RewardGrantDTO:
    id: int
    reward_name: str
    is_stackable: bool

# --- Prompts DTOs ---

@dataclass(frozen=True)
class EventPromptDTO:
    id: int
    event_id: int
    group: str | None
    day_index: int | None
    code: str
    label: str
    is_active: bool
    created_by: str
    created_at: str
    modified_by: str | None
    modified_at: str | None

@dataclass(frozen=True)
class UserActionPromptDTO:
    id: int
    user_action_id: int
    event_prompt_id: int

# --- Reporting DTOs ---

@dataclass(frozen=True)
class PromptPopularityDTO:
    event_id: int
    prompt_id: int
    prompt_code: str
    prompt_label: str
    uses: int

@dataclass(frozen=True)
class UserPromptStatsDTO:
    event_id: int
    user_id: int
    total_tagged: int
    unique_prompts: int

@dataclass(frozen=True)
class UserPromptUsageDTO:
    event_id: int
    user_id: int
    prompt_id: int
    prompt_code: str
    count: int

# --- Action Event DTOs ---

@dataclass(frozen=True)
class ActionEventDTO:
    id: int
    action_event_key: str
    event_id: int
    action_id: int
    action_description: str
    variant: str

    input_fields: list[str]             
    input_help_map: dict[str, str]      

    # availability & rules
    is_self_reportable: bool
    is_repeatable: bool
    is_allowed_during_visible: bool
    action_is_active: bool              
    is_numeric_multiplier: bool        

    # rewards/points
    points_granted: int
    has_direct_reward: bool 

    # prompt-specific
    prompts_required: bool
    prompts_group: str | None

@dataclass(frozen=True)
class UserActionCreateDTO:
    user_discord_id: str
    action_event_id: int
    url_value: str | None
    numeric_value: int | None           
    text_value: str | None
    boolean_value: bool | None         
    date_value: str | None              # raw string (YYYY-MM-DD)

@dataclass(frozen=True)
class ActionReportResultDTO:
    # points
    points_base: int
    points_awarded: int
    numeric_applied: bool

    # reward/event/action
    reward_name: str | None  
    event_name: str
    action_label: str 

    # submitted values (typed)
    numeric_value: int | None  
    url_value: str | None  
    text_value: str | None  
    boolean_value: bool | None  
    date_value: str | None