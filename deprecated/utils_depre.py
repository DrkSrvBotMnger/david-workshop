import discord
import json
import os
from datetime import datetime
from discord.ui import View, Select
from discord import Interaction, SelectOption

# File paths
USERS_FILE = "users.json"
WAREHOUSE_FILE = "warehouse.json"
SHOP_FILE = "shop.json"
EVENTS_FILE = "events.json"
REWARD_LOG_FILE = "reward_log.json"
EVENT_LOG_FILE = "event_log.json"

# Role IDs that can use admin/mod commands
MOD_ROLE_IDS = [
    1386917677389582427, 849835131182383145, 930538612754382869,
    942193816880963694
]

# number of items shown in warehouse and shop per page
PAGE_SIZE = 5  


# ==== BASIC UTILS ====


def is_admin_or_mod(member: discord.Member) -> bool:
    return (member.guild_permissions.administrator
            or any(role.id in MOD_ROLE_IDS for role in member.roles))

# Load or initialize JSON

def load_json(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump([], f)
    with open(filename, "r") as f:
        return json.load(f)

def load_json_dict(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                print(f"⚠️ Warning: {path} did not return a dict. Resetting.")
                return {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


# ==== USERS ====

def get_all_users():
    return load_json_dict(USERS_FILE)

def save_all_users(data):
    save_json(USERS_FILE, data)

def get_user_data(user: discord.Member | int | str) -> dict:
    data = get_all_users()

    if isinstance(user, discord.Member):
        user_id = str(user.id)
        display_name = user.global_name
        nickname = user.nick
        username = user.name
    else:
        user_id = str(user.id)
        display_name = None
        nickname = None
        username = None

    if user_id not in data:
        data[user_id] = {
            "points": 0,
            "titles": [],
            "equipped_title": None,
            "badges": [],
            "items": [],				
            "username": username,
            "display_name": display_name,
            "nickname": nickname
        }
    else:
        if display_name:
            data[user_id]["display_name"] = display_name
        if nickname:
            data[user_id]["nickname"] = nickname               
        if username:
            data[user_id]["username"] = username

    save_all_users(data)
    return data[user_id]

def update_user_data(user_id, user_data):
    data = get_all_users()
    data[str(user_id)] = user_data
    save_all_users(data)


# ==== WAREHOUSE ====

def get_warehouse():
    return load_json(WAREHOUSE_FILE)

def save_warehouse(data):
    save_json(WAREHOUSE_FILE, data)


# ==== SHOP ====

def get_shop():
    return load_json(SHOP_FILE)

def save_shop(data):
    save_json(SHOP_FILE, data)


# ==== REWARD ====

def generate_next_reward_id(reward_type, warehouse):
    prefix = {"badge": "B", "title": "T", "item": "I"}.get(reward_type, "X")
    existing = [r["id"] for r in warehouse if r["id"].startswith(prefix)]
    max_num = max([int(r[1:]) for r in existing], default=0)
    return f"{prefix}{max_num+1:04}"


class RewardPaginator(discord.ui.View):
    def __init__(self, rewards, reward_event_map, user, mode="warehouse", events_dict=None, timeout=120):
        super().__init__(timeout=timeout)
        self.rewards = rewards
        self.reward_event_map = reward_event_map
        self.events_dict = events_dict or {}
        self.user = user
        self.page = 0
        self.max_pages = (len(rewards) - 1) // PAGE_SIZE + 1
        self.mode = mode

    def format_page(self):
        title = "📦 Reward Warehouse" if self.mode == "warehouse" else "🛒 Reward Shop"
        embed = discord.Embed(title=f"{title} (Page {self.page + 1}/{self.max_pages})", color=0x7289DA)
        chunk = self.rewards[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        for reward in chunk:
            name_line = f"**{reward['name']}** (`{reward['type']}`)"
            desc_line = reward.get("description", "No description.")
            field_lines = [f"💵 **Price:** {reward['price']} vlachka"]
            if reward["type"] == "badge":
                field_lines.insert(0, f"🏅 **Emoji:** {reward.get('emoji', '❓')}")
            elif reward["type"] == "item":
                field_lines.insert(0, f"🖼️ **Media:** [View]({reward.get('media_url', '-')})")
                field_lines.insert(0, f"📦  **Stackable:** {reward.get('stackable')}")
            if self.mode == "warehouse":
                field_lines.extend([
                    f"📈 **Bought:** {reward.get('times_bought', 0)}",
                    f"🆔 **ID:** `{reward['id']}`"])
            linked_events = self.reward_event_map.get(reward["id"], [])
            if linked_events:
                if self.mode == "shop":
                    event_names = [self.events_dict.get(eid, eid) for eid in linked_events]
                    field_lines.append(f"📎 **Event:** {', '.join(event_names)}")
                else:
                    field_lines.append(f"📎 **Events:** {', '.join(linked_events)}")
            elif self.mode == "warehouse":
                field_lines.append("❌ **Not assigned to any event**")
            embed.add_field(name=name_line, value=f"📝 *{desc_line}*\n" + "\n".join(field_lines), inline=False)
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        await interaction.response.edit_message(embed=self.format_page(), view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.format_page(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self.format_page(), view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.max_pages - 1
        await interaction.response.edit_message(embed=self.format_page(), view=self)

class EmbedPaginator(discord.ui.View):
    def __init__(self, pages):
        super().__init__(timeout=60)
        self.pages = pages
        self.current = 0
        self.prev = discord.ui.Button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
        self.next = discord.ui.Button(label="Next ➡️", style=discord.ButtonStyle.secondary)
        self.prev.callback = self.go_prev
        self.next.callback = self.go_next
        self.add_item(self.prev)
        self.add_item(self.next)
        self.update_buttons()

    def update_buttons(self):
        self.prev.disabled = self.current == 0
        self.next.disabled = self.current >= len(self.pages) - 1

    async def go_prev(self, interaction):
        self.current -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def go_next(self, interaction):
        self.current += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

def create_embed_paginator(pages):
    return EmbedPaginator(pages)


def log_reward_action(
            user_id, 
            reward_id, 
            reward_type, 
            action, 
            amount,
            reason, 
            performed_by 
            ):
    log_entry = {
        "user_id": str(user_id),
        "reward_id": reward_id,
        "reward_type": reward_type,
        "action": action,
        "amount": amount,
        "reason": reason,
        "performed_by": str(performed_by),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logs = load_json(REWARD_LOG_FILE)
    logs.append(log_entry)
    save_json(REWARD_LOG_FILE, logs)


# ==== EVENTS ====

class RewardLinkSelectView(View):
    def __init__(self, interaction, event):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.event = event
        self.result = []

        # Get rewards from warehouse
        options = []
        for reward in get_warehouse():
            label = f"({reward['id']}) {reward['name']}"
            value = reward["id"]
            options.append(SelectOption(label=label[:100], value=value))

        # Limit to 25 options as per Discord
        self.select = Select(
            placeholder="Select reward(s) to link...",
            min_values=1,
            max_values=min(5, len(options)),  # adjust as needed
            options=options[:25]
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction2: Interaction):
        if interaction2.user.id != self.interaction.user.id:
            await interaction2.response.send_message("This menu isn't for you.", ephemeral=True)
            return

        self.result = self.select.values
        self.stop()
        await interaction2.response.defer()

class RewardUnlinkSelectView(View):
    def __init__(self, interaction, event):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.event = event
        self.result = []

        reward_ids = event.get("rewards", [])
        warehouse = get_warehouse()

        options = []
        for reward in warehouse:
            if reward["id"] in reward_ids:
                label = f"({reward['id']}) {reward['name']}"
                value = reward["id"]
                options.append(SelectOption(label=label[:100], value=value))

        if not options:
            return  # no need to build view if empty

        self.select = Select(
            placeholder="Select reward(s) to unlink...",
            min_values=1,
            max_values=min(5, len(options)),
            options=options
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction2: Interaction):
        if interaction2.user.id != self.interaction.user.id:
            await interaction2.response.send_message("This menu isn't for you.", ephemeral=True)
            return

        self.result = self.select.values
        self.stop()
        await interaction2.response.defer()
        

def get_events():
    return load_json(EVENTS_FILE)

def save_events(data):
    save_json(EVENTS_FILE, data)

def get_event_by_id(event_id: str):
    events = get_events()
    return next((e for e in events if e["event_id"] == event_id or e.get("code") == event_id), None)

def generate_event_id(code: str, start_date: str):
    try:
        date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        suffix = date_obj.strftime("%m%y")
    except ValueError:
        suffix = "0000"
    return f"{code.lower()}-{suffix}"

def log_event_action(event_id, action_type, performed_by, reason=None, details=None):
    log_entry = {
        "event_id": event_id,
        "action": action_type,
        "performed_by": performed_by,
        "timestamp": datetime.utcnow().isoformat(),
        "reason": reason or "No reason provided.",
    }

    if details:
        log_entry["details"] = details

    logs = []
    logs = load_json(EVENT_LOG_FILE)
    logs.append(log_entry)
    save_json(EVENT_LOG_FILE, logs)
        
def create_event(code: str, name: str, description: str, start_date: str, end_date: str, created_by: int, **kwargs):
    events = get_events()

    event_id = generate_event_id(code, start_date)
    if any(e["event_id"] == event_id for e in events):
        raise ValueError("An event with this ID already exists.")

    event = {
        "event_id": event_id,
        "code": code,
        "name": name,
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "active": kwargs.get("active", True),
        "visible": kwargs.get("visible", True),
        "created_by": created_by,
        "created_at": datetime.utcnow().isoformat(),

        # Extended metadata
        "coordinator_id": kwargs.get("coordinator_id"),
        "rules_url": kwargs.get("rules_url"),
        "signup_url": kwargs.get("signup_url"),
        "banner_url": kwargs.get("banner_url"),
        "playlist_url": kwargs.get("playlist_url"),
        "shop_section_id": kwargs.get("shop_section_id"),
        "embed_color": kwargs.get("embed_color", 0x7289DA),
        "priority": kwargs.get("priority", 0),
        "tags": kwargs.get("tags", []),
        "custom_links": kwargs.get("custom_links", {}),
        "rewards": kwargs.get("rewards", [])
    }

    events.append(event)
    save_events(events)
    return event

def link_reward_to_event(event_id: str, reward_id: str) -> bool:
    events = get_events()
    for event in events:
        if event["event_id"] == event_id:
            if "rewards" not in event:
                event["rewards"] = []
            if reward_id not in event["rewards"]:
                event["rewards"].append(reward_id)
                save_events(events)
                return True
    return False

def unlink_reward_from_event(event_id: str, reward_id: str) -> bool:
    events = get_events()
    for event in events:
        if event["event_id"] == event_id:
            if reward_id in event.get("rewards", []):
                event["rewards"].remove(reward_id)
                save_events(events)
                return True
    return False

