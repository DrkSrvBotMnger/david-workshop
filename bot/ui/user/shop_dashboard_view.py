from discord import app_commands, Interaction, SelectOption, Embed, ButtonStyle, ui, File
from discord.ext import commands
from discord.ui import View, Button, Select
from db.database import db_session
from bot.crud import users_crud
from bot.crud.shop_crud import get_inshop_catalog_grouped
from bot.crud.purchase_crud import fetch_reward_event, apply_purchase, PurchaseError
from collections import defaultdict

TYPE_LABELS = {
    "title": "🎗️ Titles",
    "badge": "🏷️ Badges",
    "preset": "🎁 Presets",
}


        



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
                    print("✅ Fetching reward event")
                    re, rw, ev = fetch_reward_event(session, value)
                    print("✅ Applying purchase")
                    inv, price = apply_purchase(session, user, re, rw)
                    print("✅ Purchase applied")
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
            f"✅ Purchased **{reward_name}** for **{price}** points from **{event_name}**!",
            ephemeral=True
        )


class ShopPager(ui.View):
    def __init__(self, pages, user_points: int):
        super().__init__(timeout=120)
        self.pages = pages              # list of dict pages
        self.index = 0
        self.user_points = user_points
        self.filter = "all"             # "all" | "title" | "badge" | "preset"
        self._refresh_children()


    def _filtered_items(self):
        page = self.pages[self.index]
        items = page["items"]
        if self.filter == "all":
            return items
        return [it for it in items if it["reward_type"] == self.filter]

    def _make_embed(self):
        page = self.pages[self.index]
        emb = Embed(title=f"🛍️ {page['event_name']}", description="Pick an item to preview & buy.")

        items = self._filtered_items()

        if self.filter == "all":
            # group into sections
            by_type = {"title": [], "badge": [], "preset": []}
            for it in items:
                by_type.get(it["reward_type"], []).append(it)

            for t in ["title", "badge", "preset"]:
                if not by_type[t]:
                    continue
                emb.add_field(name=TYPE_LABELS[t], value="", inline=False)
                for it in by_type[t]:
                    emb.add_field(
                        name="\n",
                        value=f"**{it['reward_name']}** — {it['price']} vlachki :coin:",
                        inline=False,
                    )
        else:
            # single section
            if items:
                emb.add_field(name=TYPE_LABELS[self.filter], value="\u200b", inline=False)
                for it in items:
                    emb.add_field(
                        name="\n",
                        value=f"**{it['reward_name']}** — {it['price']} vlachki :coin:",
                        inline=False,
                    )
            else:
                emb.add_field(name=TYPE_LABELS[self.filter], value="(No items)", inline=False)

        emb.set_footer(text=f"Your wallet: {self.user_points} vlachki")
        return emb
    
    
    def _refresh_children(self):
        self.clear_items()

        # === page nav ===
        prev_btn = ui.Button(label="◀ Prev", style=ButtonStyle.secondary, custom_id="shop_prev")
        next_btn = ui.Button(label="Next ▶", style=ButtonStyle.secondary, custom_id="shop_next")

        async def flip(i: Interaction):
            if i.data["custom_id"] == "shop_prev":
                self.index = (self.index - 1) % len(self.pages)
            else:
                self.index = (self.index + 1) % len(self.pages)
            self._refresh_children()
            await i.response.edit_message(embed=self._make_embed(), view=self)

        prev_btn.callback = flip
        next_btn.callback = flip
        self.add_item(prev_btn)
        self.add_item(next_btn)

        # === type filters ===
        def make_filter_button(label, value):
            style = ButtonStyle.primary if self.filter == value else ButtonStyle.secondary
            btn = ui.Button(label=label, style=style, custom_id=f"flt_{value}")
            async def cb(i: Interaction, v=value):
                self.filter = v
                self._refresh_children()
                await i.response.edit_message(embed=self._make_embed(), view=self)
            btn.callback = cb
            return btn

        self.add_item(make_filter_button("All", "all"))
        self.add_item(make_filter_button("Titles", "title"))
        self.add_item(make_filter_button("Badges", "badge"))
        self.add_item(make_filter_button("Presets", "preset"))
        self.add_item(
            ui.Button(
                label="How it looks",
                style=ButtonStyle.link,
                url="PREVIEW_URL"
            )
        )

        # === select for the currently filtered list ===
        page = self.pages[self.index]
        items = self._filtered_items()
        opts = [
            SelectOption(
                label=f"{it['reward_name']} — {it['price']} pts"[:100],
                value=it['reward_event_key'][:100],
            )
            for it in items[:25]
        ]
        self.add_item(ShopSelect(opts))

    async def interaction_check(self, interaction: Interaction) -> bool:
        return True

    
    @commands.Cog.listener()
    async def on_interaction(self, interaction):  # not needed if we handle button callbacks below in the cog
        pass