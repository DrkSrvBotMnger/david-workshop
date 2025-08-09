import discord
from discord.ui import View, Button

class EmbedPaginator(View):
    """
    Simple embed paginator with first/prev/next/last controls.
    Call with a prebuilt list of embeds.
    """
    def __init__(self, pages: list[discord.Embed], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

        self.first_button = Button(emoji="⏮️", style=discord.ButtonStyle.secondary)
        self.prev_button  = Button(emoji="◀️",  style=discord.ButtonStyle.secondary)
        self.next_button  = Button(emoji="▶️",  style=discord.ButtonStyle.secondary)
        self.last_button  = Button(emoji="⏭️",  style=discord.ButtonStyle.secondary)

        self.first_button.callback = self.go_first
        self.prev_button.callback  = self.prev_page
        self.next_button.callback  = self.next_page
        self.last_button.callback  = self.go_last

        self.add_item(self.first_button)
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.last_button)

        self._update_footer()

    async def _apply_state(self, interaction: discord.Interaction):
        # enable all, then disable as needed
        for child in self.children:
            child.disabled = False

        if self.current_page == 0:
            self.first_button.disabled = True
            self.prev_button.disabled = True
        if self.current_page == len(self.pages) - 1:
            self.next_button.disabled = True
            self.last_button.disabled = True

        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    def _update_footer(self):
        for i, embed in enumerate(self.pages):
            embed.set_footer(text=f"Page {i + 1} of {len(self.pages)}")

    async def go_first(self, interaction: discord.Interaction):
        if self.current_page != 0:
            self.current_page = 0
            await self._apply_state(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self._apply_state(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self._apply_state(interaction)

    async def go_last(self, interaction: discord.Interaction):
        last = len(self.pages) - 1
        if self.current_page != last:
            self.current_page = last
            await self._apply_state(interaction)


async def paginate_embeds(interaction: discord.Interaction, embeds: list[discord.Embed], ephemeral: bool = True):
    """
    Convenience helper to send a paginated embed message.
    """
    if not embeds:
        await interaction.followup.send("❌ No data to display.", ephemeral=True)
        return

    paginator = EmbedPaginator(embeds)

    # Initial state
    if len(embeds) == 1:
        for child in paginator.children:
            child.disabled = True
    else:
        paginator.first_button.disabled = True
        paginator.prev_button.disabled = True

    await interaction.followup.send(embed=embeds[0], view=paginator, ephemeral=ephemeral)