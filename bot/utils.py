import discord
from datetime import datetime
from discord import Interaction, ui
from discord.ui import View, Button
from typing import Optional
from bot.config import MOD_ROLE_IDS


# Parse common date strings into YYYY-MM-DD format
def safe_parse_date(date_str: str) -> str | None:
    """Attempts to parse a date string into YYYY-MM-DD. Returns None if invalid."""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def format_discord_timestamp(iso_str, style="F"):
    try:
        dt = datetime.fromisoformat(iso_str)
        unix_ts = int(dt.timestamp())
        return f"<t:{unix_ts}:{style}>"
    except Exception:
        return iso_str

# Check if user is a member of the moderator roles definied in config.py
async def is_admin_or_mod(interaction: Interaction) -> bool:
    try:
        if interaction.guild is None:
            return False
        member = await interaction.guild.fetch_member(interaction.user.id)
    except discord.NotFound:
        return False

    return (
        member.guild_permissions.administrator or
        any(role.id in MOD_ROLE_IDS for role in member.roles)
    )

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
            await self.message.edit(content="⌛ Confirmation timed out. No action taken.", view=self)

    @ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()

# Generic confirmation dialog
async def confirm_action(interaction: discord.Interaction, item_name: str, reason: str) -> bool:

    print("in confirm_action")
    view = ConfirmActionView()
    msg = (
        f"🗑️ Are you sure you want to delete **{item_name}**?\n"
        f"This cannot be undone.\n"
    )
    
    view.message = await interaction.edit_original_response(content=msg, view=view)
    await view.wait()
    
    return view.confirmed is True


# Embed paginator for displaying multiple embeds in a single message
class EmbedPaginator(View):
    def __init__(self, pages: list[discord.Embed], timeout=60):
        
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

        # Buttons
        self.first_button = Button(emoji="⏮️", style=discord.ButtonStyle.secondary)
        self.prev_button = Button(emoji="◀️", style=discord.ButtonStyle.secondary)
        self.next_button = Button(emoji="▶️", style=discord.ButtonStyle.secondary)
        self.last_button = Button(emoji="⏭️", style=discord.ButtonStyle.secondary)
        
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

        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
            
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
            
async def paginate_embeds(interaction: discord.Interaction, embeds: list[discord.Embed]):
    if not embeds:
        await interaction.followup.send("❌ No data to display.", ephemeral=True)
        return
    paginator = EmbedPaginator(embeds)

    # Set initial button states based on page 0
    if len(embeds) == 1:
        for child in paginator.children:
            child.disabled = True
    else:
        paginator.first_button.disabled = True
        paginator.prev_button.disabled = True
        
    await interaction.followup.send(embed=embeds[0], view=paginator, ephemeral=True)


# Format log entries for display in embeds or paginated lists
def format_log_entry(
    action: str,
    performed_by: str,
    timestamp: str,
    description: Optional[str] = None,
    label: Optional[str] = None
) -> str:
    """
    Format a generic log entry for display in embeds or paginated lists.

    Args:
        action (str): Action performed (e.g., create, edit, delete)
        performed_by (str): Discord user ID of the person who performed the action
        timestamp (str): UTC timestamp as string
        description (str, optional): Extra description of the action
        label (str, optional): Optional object label, like "Event", "Reward", etc.

    Returns:
        str: Formatted line to display
    """
    from datetime import datetime

    # Convert timestamp to local-friendly format
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
        formatted_ts = f"<t:{int(dt.timestamp())}:f>"
    except Exception:
        formatted_ts = timestamp  # fallback if parsing fails

    label_prefix = f"**{label}:** " if label else ""
    description_part = f" — {description}" if description else ""

    return f"{label_prefix}**{action.capitalize()}** by <@{performed_by}> at {formatted_ts}{description_part}"
