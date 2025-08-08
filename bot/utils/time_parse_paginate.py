import discord
from datetime import datetime, timezone
from discord import Interaction, ui, Message
from discord.ui import View, Button
from typing import Optional
from bot.config import MOD_ROLE_IDS, SUPPORTED_FIELDS


# ISO 8601 format with timezone offset
def now_iso():
    """
    Returns current UTC time in ISO 8601 format with timezone offset.
    Example: '2025-07-30T14:35:22+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


# Unix timestamp (int)
def now_unix():
    """
    Current UTC time as Unix timestamp (int).
    Example: '1753971557'
    """
    return int(datetime.now(timezone.utc).timestamp())


# Parse common date strings into YYYY-MM-DD format
def safe_parse_date(date_str: str) -> str | None:
    """Attempts to parse a date string into YYYY-MM-DD. Returns None if invalid."""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(),
                                     fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# Format dates to be recognized by discord as timestamps
def format_discord_timestamp(
    iso_str: str, 
    style: str="F"
) -> str:
    """ format dates to be recognized by discord as timestamps """
    
    try:
        dt = datetime.fromisoformat(iso_str)
        unix_ts = int(dt.timestamp())
        return f"<t:{unix_ts}:{style}>"
    except Exception:
        return iso_str


# Supported fields for Action definitions
def parse_required_fields(input_fields_json: str | None) -> list[str]:
    """Return ordered list of required fields (subset of SUPPORTED_FIELDS)."""
    if not input_fields_json:
        return []
    try:
        fields = json.loads(input_fields_json)
    except Exception:
        return []
    out = []
    for f in fields:
        f = str(f).strip().lower()
        if f in SUPPORTED_FIELDS and f not in out:
            out.append(f)
    return out

        
# Parse Discord message links into channel_id and message_id
def parse_message_link(message_link: str) -> tuple[int, int]:
    """
    Parse a Discord message link into (channel_id, message_id).

    Args:
        message_link (str): The full message link from Discord.

    Returns:
        tuple[int, int]: (channel_id, message_id)

    Raises:
        ValueError: If the link is not in a valid Discord message link format.
    """
    try:
        parts = message_link.strip().split("/")
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
        return channel_id, message_id
    except (IndexError, ValueError):
        raise ValueError("Invalid Discord message link format.")


# Check if user is a member of the moderator roles definied in config.py
async def is_admin_or_mod(interaction: Interaction) -> bool:
    try:
        if interaction.guild is None:
            return False
        member = await interaction.guild.fetch_member(interaction.user.id)
    except discord.NotFound:
        return False

    return (member.guild_permissions.administrator
            or any(role.id in MOD_ROLE_IDS for role in member.roles))

def admin_or_mod_check():
    return discord.app_commands.check(is_admin_or_mod)


# Confirmation actions
class ConfirmActionView(ui.View):

    def __init__(self, timeout: int = 30):

        super().__init__(timeout=timeout)
        self.confirmed: Optional[bool] = None
        self.message: Optional[discord.Message] = None

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                if isinstance(child, ui.Button):
                    child.disabled = True
            await self.message.edit(
                content="⌛ Confirmation timed out. No action taken.",
                view=self)

    @ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction,
                      button: ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction,
                     button: ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()

# Generic confirmation dialog
async def confirm_action(
    interaction: discord.Interaction, 
    item_name: str,
    item_action: str,
    reason: str
) -> bool:

    view = ConfirmActionView()
    msg=""
    if item_action == "delete":
        msg = (
            f"🗑️ Are you sure you want to delete **{item_name}**?\n"
            f"This cannot be undone.\n"
        )
    if item_action == "force_update":
        msg = (
            f"⚠️ Are you sure you want to update **{item_name}**?\n"
            f"This cannot be undone.\n"
        )
    if item_action == "force_delete":
        msg = (
            f"⚠️ Are you **really** sure you want to delete **{item_name}**?\n"
            f"This cannot be undone.\n"
        )

    view.message = await interaction.edit_original_response(content=msg,
                                                            view=view)
    await view.wait()

    return view.confirmed is True


# Embed paginator for displaying multiple embeds in a single message
class EmbedPaginator(View):

    def __init__(self, pages: list[discord.Embed], timeout=60):

        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

        # Buttons
        self.first_button = Button(emoji="⏮️",
                                   style=discord.ButtonStyle.secondary)
        self.prev_button = Button(emoji="◀️",
                                  style=discord.ButtonStyle.secondary)
        self.next_button = Button(emoji="▶️",
                                  style=discord.ButtonStyle.secondary)
        self.last_button = Button(emoji="⏭️",
                                  style=discord.ButtonStyle.secondary)

        self.first_button.callback = self.go_first
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.last_button.callback = self.go_last

        self.add_item(self.first_button)
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.last_button)

        self.update_footer()

    async def update_buttons(self, interaction):
        for child in self.children:
            child.disabled = False

        if self.current_page == 0:
            self.first_button.disabled = True
            self.prev_button.disabled = True
        if self.current_page == len(self.pages) - 1:
            self.next_button.disabled = True
            self.last_button.disabled = True

        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self)

    def update_footer(self):
        for i, embed in enumerate(self.pages):
            embed.set_footer(text=f"Page {i + 1} of {len(self.pages)}")

    async def go_first(self, interaction: discord.Interaction):
        if self.current_page != 0:
            self.current_page = 0
            await self.update_buttons(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_buttons(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_buttons(interaction)

    async def go_last(self, interaction: discord.Interaction):
        if self.current_page != len(self.pages) - 1:
            self.current_page = len(self.pages) - 1
            await self.update_buttons(interaction)


async def paginate_embeds(interaction: discord.Interaction,
                          embeds: list[discord.Embed]):
    if not embeds:
        await interaction.followup.send("❌ No data to display.",
                                        ephemeral=True)
        return
    paginator = EmbedPaginator(embeds)

    # Set initial button states based on page 0
    if len(embeds) == 1:
        for child in paginator.children:
            child.disabled = True
    else:
        paginator.first_button.disabled = True
        paginator.prev_button.disabled = True

    await interaction.followup.send(embed=embeds[0],
                                    view=paginator,
                                    ephemeral=True)


# Format log entries for display in embeds or paginated lists
def format_log_entry(log_action: str,
                     performed_by: str,
                     performed_at: str,
                     log_description: Optional[str] = None,
                     label: Optional[str] = None) -> str:
    """
    Format a generic log entry for display in embeds or paginated lists.

    Args:
        log_action (str): Action performed (e.g., create, edit, delete)
        performed_by (str): Discord user ID of the person who performed the action
        performed_at (str): UTC timestamp as string
        log_description (str, optional): Extra description of the action
        label (str, optional): Optional object label, like "Event", "Reward", etc.

    Returns:
        str: Formatted line to display
    """
    # Convert performed_at to local-friendly format
    try:
        dt = datetime.strptime(performed_at, "%Y-%m-%d %H:%M:%S.%f")
        formatted_ts = f"<t:{int(dt.timestamp())}:f>"
    except Exception:
        formatted_ts = performed_at  # fallback if parsing fails

    label_prefix = f"**{label}:** " if label else ""
    description_part = f" — {log_description}" if log_description else ""

    return f"{label_prefix}**{log_action.capitalize()}** by <@{performed_by}> at {formatted_ts}{description_part}"


## Announcement messages
async def post_announcement_message(
    interaction: discord.Interaction, 
    announcement_channel_id: str,
    msg: str,
    role_discord_id: Optional[str] = None
) -> Optional[Message]:
    """Post announcement in announcement channel"""

    try:
        announcement_channel = interaction.guild.get_channel(int(announcement_channel_id))
        if not announcement_channel:
            print(f"⚠️ Announcement channel {announcement_channel_id} not found.")
            return None

        # Add role ping if applicable
        if role_discord_id:
            msg = f"<@&{role_discord_id}>\n{msg}"

        return await announcement_channel.send(msg)

    except Exception as e:
        print(f"⚠️ Failed to post message in channel: {e}")
        return None