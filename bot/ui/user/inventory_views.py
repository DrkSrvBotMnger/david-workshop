import discord
from typing import Iterable, Awaitable, Callable, Optional

class InventoryView(discord.ui.View):
    def __init__(
        self,
        viewer: discord.abc.User | discord.Member,
        items: Iterable[dict],
        on_back_to_profile: Optional[Callable[[discord.Interaction], Awaitable[None]]] = None,
        display_name: Optional[str] = None,
    ):
        super().__init__(timeout=120)
        self.viewer = viewer
        self.items = list(items)
        self._on_back = on_back_to_profile
        self.display_name = display_name

        if self._on_back:
            btn = discord.ui.Button(label="← Back to Profile", style=discord.ButtonStyle.secondary, custom_id="inventory:back_profile")
            async def _go_back(inter: discord.Interaction):
                await self._on_back(inter)
            btn.callback = _go_back
            self.add_item(btn)

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
