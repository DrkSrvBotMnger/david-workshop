import discord
from discord import ui
from typing import Optional

class ConfirmActionView(ui.View):
    """Simple yes/no confirm view. Set .message after sending to enable timeout edits."""
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
                view=self
            )

    @ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _: ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()

async def confirm_action(
    interaction: discord.Interaction,
    item_name: str,
    item_action: str,
    reason: str | None = None
) -> bool:
    """
    Generic confirmation dialog.
    Returns True if user confirmed, False otherwise.
    """
    view = ConfirmActionView()

    # Compose message
    if item_action == "delete":
        msg = f"🗑️ Are you sure you want to delete **{item_name}**?\nThis cannot be undone."
    elif item_action == "force_update":
        msg = f"⚠️ Are you sure you want to update **{item_name}**?\nThis cannot be undone."
    elif item_action == "force_delete":
        msg = f"⚠️ Are you **really** sure you want to delete **{item_name}**?\nThis cannot be undone."
    else:
        msg = f"Proceed with **{item_action}** on **{item_name}**?"

    if reason:
        msg += f"\nReason: {reason}"

    view.message = await interaction.edit_original_response(content=msg, view=view)
    await view.wait()
    return view.confirmed is True