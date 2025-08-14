import discord
from typing import Iterable, Awaitable, Callable, Optional, Dict, Tuple

class PresetPreviewButton(discord.ui.Button):
    def __init__(self, owner_id: int, preset_map: dict[str, tuple[str, str, str]]):
        super().__init__(style=discord.ButtonStyle.secondary, label="Preview publishables")
        self.owner_id = owner_id
        self.preset_map = preset_map

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the inventory owner can open previews.", ephemeral=True
            )
            return
        view = PresetPreviewView(owner_id=self.owner_id, preset_map=self.preset_map)
        try:
            await interaction.response.send_message(
                "🎛️ **Choose an item to preview:**",
                view=view,
                ephemeral=True
            )
        except discord.InteractionResponded:
            # If something already responded, fall back to followup (still ephemeral)
            await interaction.followup.send(
                "🎛️ **Choose an item to preview:**",
                view=view,
                ephemeral=True
            )

class PresetPreviewView(discord.ui.View):
    def __init__(self, owner_id: int, preset_map: Dict[str, Tuple[str, str, str]]):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.preset_map = preset_map
        self.add_item(PresetSelect(self.preset_map))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the inventory owner can use this.", ephemeral=True
            )
            return False
        return True

class PresetSelect(discord.ui.Select):
    def __init__(self, preset_map: Dict[str, Tuple[str, str, str]]):
        self.preset_map = preset_map
        options = [
            discord.SelectOption(label=meta[2][:100] or "Publishable", value=val[:100])
            for (val, meta) in preset_map.items()
        ]
        super().__init__(placeholder="Select…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # This is the EPHEMERAL message we just sent above
        ephemeral_msg_id = interaction.message.id
    
        await interaction.response.defer(ephemeral=True)
    
        chosen = self.values[0]
        ch, msg, _ = self.preset_map.get(chosen, (None, None, None))
        if not (ch and msg):
            await interaction.followup.edit_message(
                message_id=ephemeral_msg_id,
                content="⚠️ Missing source message.",
                embeds=[],
                attachments=[],
                view=self.view
            )
            return
    
        try:
            channel = interaction.guild.get_channel(int(ch)) or await interaction.client.fetch_channel(int(ch))
            src_msg = await channel.fetch_message(int(msg))
        except Exception:
            await interaction.followup.edit_message(
                message_id=ephemeral_msg_id,
                content="⚠️ Could not fetch (permissions or deleted).",
                embeds=[],
                attachments=[],
                view=self.view
            )
            return
    
        content = src_msg.content or None
        embeds = src_msg.embeds[:10] if src_msg.embeds else []
    
        files = []
        try:
            for a in src_msg.attachments:
                if (a.content_type and a.content_type.startswith("image/")) or a.filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".webp")
                ):
                    if len(files) >= 10:
                        break
                    files.append(await a.to_file())
        except Exception:
            files = []
    
        await interaction.followup.edit_message(
            message_id=ephemeral_msg_id,
            content=content,
            embeds=embeds,
            attachments=files,
            view=self.view
        )

class InventoryView(discord.ui.View):
    """
    Inventory view. Receives a list of items to display.
    """
    def __init__(
        self,
        viewer: discord.abc.User | discord.Member,
        items: Iterable[dict],
        on_view_profile: Optional[Callable[[discord.Interaction], Awaitable[None]]] = None,
        display_name: Optional[str] = None,
        *,
        author_id: int,  
        publishables: dict[str, tuple[str, str, str]] | None = None, 
    ):
        super().__init__(timeout=120)
        self.viewer = viewer
        self.items = list(items)
        self._on_view = on_view_profile
        self.display_name = display_name
        self.author_id = author_id
        if publishables: 
            self.add_item(PresetPreviewButton(owner_id=self.viewer.id, preset_map=publishables))

        if self._on_view:
            btn = discord.ui.Button(label="View Profile", style=discord.ButtonStyle.primary, custom_id="inventory:view_profile")
            async def _go_view(inter: discord.Interaction):
                await self._on_view(inter)
            btn.callback = _go_view
            self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This inventory panel isn’t yours.", ephemeral=True)
            return False
        return True

    @staticmethod
    def _equipped_suffix(is_equipped: bool, rtype: str) -> str:
        return " • equipped" if rtype in ("title", "badge") and is_equipped else ""

    @staticmethod
    def _fmt_title(name: str, is_equipped: bool) -> str:
        return f" • {name}" + InventoryView._equipped_suffix(is_equipped, "title")

    @staticmethod
    def _fmt_badge(name: str, emoji: str | None, is_equipped: bool) -> str:
        right = f" • {emoji}" if emoji else ""
        return f" • {name}{right}" + InventoryView._equipped_suffix(is_equipped, "badge")

    @staticmethod
    def _fmt_preset(name: str) -> str:
        return f" • {name}"

    def _group(self):
        t, b, p = [], [], []
        for it in self.items:
            rt = it["reward_type"]
            if rt == "title":
                t.append(self._fmt_title(it["reward_name"], it["is_equipped"]))
            elif rt == "badge":
                b.append(self._fmt_badge(it["reward_name"], it.get("emoji"), it["is_equipped"]))
            elif rt == "preset":
                p.append(self._fmt_preset(it["reward_name"]))
            else:
                p.append(self._fmt_preset(it["reward_name"]))
        return t, b, p

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f"🎒 Inventory — {self.display_name}")
        t, b, p = self._group()
        if t: embed.add_field(name="📜 Titles", value="\n".join(t)[:1024], inline=False)
        if b: embed.add_field(name="🏅 Badges", value="\n".join(b)[:1024], inline=False)
        if p: embed.add_field(name="🧰 Presets", value="\n".join(p)[:1024], inline=False)
        if not (t or b or p): embed.description = "No rewards yet."
        return embed