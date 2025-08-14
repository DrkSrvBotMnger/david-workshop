from discord import app_commands, Interaction, SelectOption, Embed, ButtonStyle, ui, File
from discord.ext import commands
from discord.ui import View, Button, Select
from db.database import db_session
from bot.config.constants import CURRENCY
from bot.crud import users_crud
from bot.crud.shop_crud import get_inshop_catalog_grouped
from bot.crud.purchase_crud import fetch_reward_event, apply_purchase, PurchaseError
from collections import defaultdict

TYPE_LABELS = {
    "title": "🎗️ Titles",
    "badge": "🏷️ Badges",
    "preset": "🎁 Presets",
}

TYPE_ORDER = ["title", "badge", "preset"]

def _name_with_emoji(it: dict) -> str:
    """For badges, show emoji + name; otherwise just the name."""
    if it.get("reward_type") == "badge" and it.get("emoji"):
        
        return f"**{it['reward_name']}** • {it['emoji']}"
    return f"**{it['reward_name']}**"
    
def _items_for_event_page(self):
    """Items for the current event page, honoring self.filter."""
    page = self.pages[self.index]
    items = page["items"]
    if self.filter != "all":
        items = [it for it in items if it["reward_type"] == self.filter]
    return items

def _items_for_type_tab(self):
    """All items of self.type_cursor across ALL events."""
    t = self.type_cursor
    out = []
    for p in self.pages:
        ev_name = p["event_name"]
        for it in p["items"]:
            if it["reward_type"] == t:
                # Enrich with event for labeling in the select
                out.append({**it, "_event_name": ev_name})
    return out

class ShopSelect(Select):
    def __init__(self, options):
        super().__init__(placeholder="Choose a reward to buy…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        value = self.values[0]  # reward_event_key
        async with interaction.channel.typing():
            with db_session() as session:
                user = users_crud.get_or_create_user(session, interaction.user)
                print("before the try block")
                try:
                    
                    re, rw, ev = fetch_reward_event(session, value)
                    inv, price = apply_purchase(session, user, re, rw)
                    reward_name=rw.reward_name
                    event_name=ev.event_name
                    session.flush()
                    
                except PurchaseError as e:
                    await interaction.response.send_message(f"❌ {e}", ephemeral=True)
                    return
                except Exception as e:
                    session.rollback()
                    await interaction.response.send_message("❌ Purchase failed. Try again.", ephemeral=True)
                    return

        await interaction.response.send_message(
            f"✅ Purchased **{reward_name}** for **{price}** {CURRENCY} from **{event_name}**!",
            ephemeral=True
        )


class ShopPager(ui.View):
    def __init__(self, pages, user_points: int):
        super().__init__(timeout=120)
        self.pages = pages              # list of dict pages
        self.index = 0
        self.user_points = user_points
        
        self.layout = "event"           
        self.type_cursor = "title"      
        
        self.filter = "all"             # "all" | "title" | "badge" | "preset"
        self._refresh_children()


    def _filtered_items(self):
        page = self.pages[self.index]
        items = page["items"]
        if self.filter == "all":
            return items
        return [it for it in items if it["reward_type"] == self.filter]

    def _make_embed(self):
        if self.layout == "event":
            page = self.pages[self.index]
            emb = Embed(
                title=f"🛍️ {page['event_name']}",
                description="Pick an item to preview & buy.",
                color=0x1c1b18
            )
            items = _items_for_event_page(self)

            by_type = {"title": [], "badge": [], "preset": []}
            for it in items:
                by_type.get(it["reward_type"], []).append(it)

            for t in TYPE_ORDER:
                if not by_type[t]: continue
                emb.add_field(name=f"__{TYPE_LABELS[t]}__", value="\n", inline=False)
                for it in by_type[t]:
                    emb.add_field(
                        name=f"{_name_with_emoji(it)} • {it['price']} {CURRENCY} :coin:",
                        value=f"{it['reward_description'] if it['reward_description'] else ''}",
                        inline=False,
                        )

        else:
            # layout == "type"
            t = self.type_cursor
            emb = Embed(
                title=f"{TYPE_LABELS[t]} — all events",
                description="Pick an item to preview & buy.",
                color=0xfac011
            )
            items = _items_for_type_tab(self)
            if items:
                for it in items:
                    emb.add_field(
                        name=f"{_name_with_emoji(it)} • {it['price']} {CURRENCY} :coin:\nfrom {it['_event_name']}",
                        value=f"{it['reward_description'] if it['reward_description'] else ''}",
                        inline=False,
                    )
            else:
                emb.add_field(name="\n", value="(No items across events)", inline=False)

        emb.set_footer(text=f"Your wallet: {self.user_points} {CURRENCY}")
        return emb
    
    
    def _refresh_children(self):
        self.clear_items()

        # === Prev / Next ===
        prev_btn = ui.Button(label="◀ Prev", style=ButtonStyle.secondary, custom_id="shop_prev")
        next_btn = ui.Button(label="Next ▶", style=ButtonStyle.secondary, custom_id="shop_next")

        async def flip(i: Interaction):
            if self.layout == "event":
                # normal page cycling by event
                if i.data["custom_id"] == "shop_prev":
                    self.index = (self.index - 1) % len(self.pages)
                else:
                    self.index = (self.index + 1) % len(self.pages)
            else:
                # type tab cycling
                cur = TYPE_ORDER.index(self.type_cursor)
                if i.data["custom_id"] == "shop_prev":
                    cur = (cur - 1) % len(TYPE_ORDER)
                else:
                    cur = (cur + 1) % len(TYPE_ORDER)
                self.type_cursor = TYPE_ORDER[cur]

            # optional: if event mode + current filter yields 0 items, reset to all
            if self.layout == "event" and not _items_for_event_page(self):
                self.filter = "all"

            self._refresh_children()
            await i.response.edit_message(embed=self._make_embed(), view=self)

        prev_btn.callback = flip
        next_btn.callback = flip
        self.add_item(prev_btn)
        self.add_item(next_btn)

        # === Layout toggle ===
        layout_btn = ui.Button(
            label="Switch By Type" if self.layout == "event" else "Switch By Event",
            style=ButtonStyle.primary,
            custom_id="shop_layout_toggle"
        )
        async def toggle_layout(i: Interaction):
            self.layout = "type" if self.layout == "event" else "event"
            # keep cursor sane
            if self.layout == "type":
                self.type_cursor = self.type_cursor if self.type_cursor in TYPE_ORDER else "title"
            self._refresh_children()
            await i.response.edit_message(embed=self._make_embed(), view=self)
        layout_btn.callback = toggle_layout
        self.add_item(layout_btn)

        # (Optional) keep your preview link
        self.add_item(ui.Button(label="How it looks", style=ButtonStyle.link,
                                url="https://i.ibb.co/rG91q48n/demo-profile.png"))

        # === Build the Select ===
        if self.layout == "event":
            items = _items_for_event_page(self)
            if items:
                opts = [
                    SelectOption(
                        label=f"{it['reward_name'][:80]} — {it['price']} {CURRENCY} — {it['reward_type']}"[:100],
                        value=it['reward_event_key'][:100],
                    ) for it in items[:25]
                ]
                self.add_item(ShopSelect(opts))
            else:
                self.add_item(
                    Select(
                        placeholder="No items in this category for this event",
                        min_values=1, max_values=1,
                        options=[SelectOption(label="— nothing to buy —", value="noop")],
                        disabled=True,
                    )
                )
        else:
            # layout == "type" — one type tab across all events
            items = _items_for_type_tab(self)
            if items:
                opts = [
                    SelectOption(
                        # include event name in label so user knows the source
                        label=f"{it['reward_name'][:80]} — {it['price']} {CURRENCY}"[:100],
                        value=it['reward_event_key'][:100],
                    ) for it in items[:25]  # 25 max in a Discord select
                ]
                self.add_item(ShopSelect(opts))
            else:
                self.add_item(
                    Select(
                        placeholder=f"No {TYPE_LABELS[self.type_cursor]} available across events",
                        min_values=1, max_values=1,
                        options=[SelectOption(label="— nothing to buy —", value="noop")],
                        disabled=True,
                    )
                )


    async def interaction_check(self, interaction: Interaction) -> bool:
        return True

    
    @commands.Cog.listener()
    async def on_interaction(self, interaction):  # not needed if we handle button callbacks below in the cog
        pass