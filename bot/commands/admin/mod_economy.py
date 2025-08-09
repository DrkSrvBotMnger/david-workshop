# bot/commands/admin/mod_panel.py
from __future__ import annotations

import discord
from discord import app_commands, Interaction, Member
from discord.ext import commands
from sqlalchemy import func, or_

from db.database import db_session
from db.schema import Reward, Inventory
from bot.crud.users_crud import get_or_create_user
from bot.utils.time_parse_paginate import admin_or_mod_check  # your mod check
from bot.config import PUBLISHABLE_REWARD_TYPES

PUBLISHABLE_SET = {str(t).lower().strip() for t in PUBLISHABLE_REWARD_TYPES}

# ---------- helpers ----------
def _clip(s: str | None, n: int = 100) -> str:
    return (s or "").replace("\n", " ").strip()[:n]

def display_name_from_db_user(db_user) -> str:
    return (db_user.nickname or db_user.display_name or db_user.username or "").strip() or "Unknown"

def is_grantable_reward_row(rtype: str | None, preset_at: str | None) -> bool:
    rtype_l = (rtype or "").lower().strip()
    needs_publish = rtype_l in PUBLISHABLE_SET
    published = bool((preset_at or "").strip()) if isinstance(preset_at, str) else bool(preset_at)
    return (not needs_publish) or published

def list_grantable_rewards(session, exclude_keys: set[str], q: str) -> list[tuple[str, str]]:
    # fetch candidates by text
    base = session.query(Reward.reward_key, Reward.reward_name, Reward.reward_type, Reward.preset_at)
    if q:
        like = f"%{q.lower()}%"
        base = base.filter(or_(
            func.lower(Reward.reward_key).like(like),
            func.lower(Reward.reward_name).like(like),
        ))
    rows = base.order_by(Reward.reward_key.asc()).limit(200).all()

    out: list[tuple[str, str]] = []
    for rk, rn, rtype, preset_at in rows:
        if not rk or rk in exclude_keys:
            continue
        if is_grantable_reward_row(rtype, preset_at):
            out.append((rk, rn))
        if len(out) >= 25:
            break
    return out

def list_owned_rewards(session, user_id: int, q: str) -> list[tuple[str, str]]:
    query = (
        session.query(Reward.reward_key, Reward.reward_name)
        .join(Inventory, Inventory.reward_id == Reward.id)
        .filter(Inventory.user_id == user_id)
    )
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(or_(
            func.lower(Reward.reward_key).like(like),
            func.lower(Reward.reward_name).like(like),
        ))
    return query.order_by(Reward.reward_key.asc()).limit(25).all()

# ---------- UI ----------
class PointsModal(discord.ui.Modal, title="Adjust Points"):
    amount = discord.ui.TextInput(label="Amount (positive integer)", placeholder="e.g. 50", required=True, max_length=8)
    reason = discord.ui.TextInput(label="Reason (optional)", style=discord.TextStyle.paragraph, required=False, max_length=200)

    def __init__(self, target: Member, mode: str):
        super().__init__()
        self.target = target
        self.mode = mode  # "grant" or "take"

    async def on_submit(self, interaction: Interaction):
        try:
            amt = int(str(self.amount.value).strip())
            if amt <= 0:
                raise ValueError
        except Exception:
            await interaction.response.send_message("❌ Amount must be a positive integer.", ephemeral=True)
            return

        with db_session() as session:
            db_user = get_or_create_user(session, self.target)
            if self.mode == "grant":
                db_user.points += amt
                db_user.total_earned += amt
                verb = "Granted"
                prep = "to"
            else:
                db_user.points = max(0, db_user.points - amt)
                verb = "Took"
                prep = "from"
            who = display_name_from_db_user(db_user)

        extra = f" _({str(self.reason.value).strip()})_" if self.reason.value else ""
        await interaction.response.send_message(f"✅ {verb} **{amt}** points {prep} **{who}**.{extra}", ephemeral=True)

class RewardSearchModal(discord.ui.Modal, title="Search rewards"):
    query = discord.ui.TextInput(label="Search text", placeholder="name or key (optional)", required=False, max_length=50)
    def __init__(self, picker: "RewardPicker"):
        super().__init__()
        self.picker = picker
    async def on_submit(self, interaction: Interaction):
        self.picker.search_term = (self.query.value or "").strip()
        await self.picker.refresh_options(interaction)

# --- RewardPicker ---------------------------------

class RewardPicker(discord.ui.View):
    def __init__(self, author_id: int, target: Member, mode: str):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.target = target
        self.mode = mode  # "grant" or "take"
        self.search_term = ""

        # create select with a safe placeholder so first render is valid
        self.reward_select = discord.ui.Select(
            placeholder="Choose a reward…",
            min_values=1, max_values=1,
            options=[discord.SelectOption(label="Loading…", value="__none__", default=True)]
        )
        self.reward_select.disabled = True  # enable after real options arrive
        self.add_item(self.reward_select)

        async def _on_select(inter: Interaction):
            if inter.user.id != self.author_id:
                await inter.response.send_message("This panel isn't yours.", ephemeral=True)
                return
            if self.reward_select.values and self.reward_select.values[0] != "__none__":
                self.btn_confirm.disabled = False
            await inter.response.edit_message(view=self)
        self.reward_select.callback = _on_select  # type: ignore

    async def refresh_options(self, interaction: Interaction):
        # fetch and build options
        with db_session() as session:
            db_user = get_or_create_user(session, self.target)
            if self.mode == "grant":
                owned_keys = {
                    rk for (rk,) in session.query(Reward.reward_key)
                    .join(Inventory, Inventory.reward_id == Reward.id)
                    .filter(Inventory.user_id == db_user.id)
                    .all()
                }
                rows = list_grantable_rewards(session, exclude_keys=owned_keys, q=self.search_term)
            else:
                rows = list_owned_rewards(session, db_user.id, q=self.search_term)
        opts = [discord.SelectOption(label=_clip(rn), value=_clip(rk)) for rk, rn in rows[:25]]
        if not opts:
            msg = "No owned rewards." if self.mode == "take" and not self.search_term else "No rewards found."
            opts = [discord.SelectOption(label=msg, value="__none__", default=True)]

        # apply options and (re)enable select
        self.reward_select.options = opts
        self.reward_select.disabled = (len(opts) == 1 and opts[0].value == "__none__")
        self.btn_confirm.disabled = True

        header = f"**Grant reward to:** {self.target.mention}" if self.mode == "grant" else f"**Take reward from:** {self.target.mention}"
        await interaction.edit_original_response(content=header, view=self)



    @discord.ui.button(label="Search", style=discord.ButtonStyle.secondary, row=1)
    async def btn_search(self, interaction: Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(RewardSearchModal(self))

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, row=1)
    async def btn_confirm(self, interaction: Interaction, _: discord.ui.Button):
        if not self.reward_select.values:
            await interaction.response.send_message("Pick a reward first.", ephemeral=True)
            return
        chosen_key = self.reward_select.values[0]
        if chosen_key == "__none__":
            await interaction.response.send_message("Nothing to do.", ephemeral=True)
            return

        with db_session() as session:
            db_user = get_or_create_user(session, self.target)
            reward = session.query(Reward).filter(Reward.reward_key == chosen_key).first()
            if not reward:
                await interaction.response.send_message("❌ Unknown reward key.", ephemeral=True)
                return

            if self.mode == "grant":
                # double-check grantable at confirm time
                if not is_grantable_reward_row(reward.reward_type, reward.preset_at):
                    await interaction.response.send_message("❌ That reward type must be preset/published first.", ephemeral=True)
                    return
                inv = (
                    session.query(Inventory)
                    .filter(Inventory.user_id == db_user.id, Inventory.reward_id == reward.id)
                    .first()
                )
                if inv:
                    inv.quantity += 1
                else:
                    session.add(Inventory(user_id=db_user.id, reward_id=reward.id, quantity=1))
                verb, prep = "Granted", "to"
            else:
                inv = (
                    session.query(Inventory)
                    .filter(Inventory.user_id == db_user.id, Inventory.reward_id == reward.id)
                    .first()
                )
                if not inv:
                    await interaction.response.send_message("⚠️ User does not own that reward.", ephemeral=True)
                    return
                if inv.quantity > 1:
                    inv.quantity -= 1
                else:
                    session.delete(inv)
                verb, prep = "Removed", "from"

            who = display_name_from_db_user(db_user)
            rname, rkey = reward.reward_name, reward.reward_key

        await interaction.response.send_message(f"✅ {verb} **{rname}** (`{rkey}`) {prep} **{who}**.", ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.gray, row=1)
    async def btn_back(self, interaction: Interaction, _: discord.ui.Button):
        menu = ActionMenu(author_id=self.author_id, target=self.target)
        await interaction.response.edit_message(
            content=f"**Target:** {self.target.mention}",
            view=menu
        )

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True

class ActionMenu(discord.ui.View):
    def __init__(self, author_id: int, target: Member):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.target = target

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Grant Points", style=discord.ButtonStyle.success, row=0)
    async def btn_grant_points(self, interaction: Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(PointsModal(self.target, mode="grant"))

    @discord.ui.button(label="Take Points", style=discord.ButtonStyle.danger, row=0)
    async def btn_take_points(self, interaction: Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(PointsModal(self.target, mode="take"))

    # --- inside ActionMenu ---


    @discord.ui.button(label="Grant Reward", style=discord.ButtonStyle.primary, row=1)
    async def btn_grant_reward(self, interaction: Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        picker = RewardPicker(self.author_id, self.target, mode="grant")
        # do NOT edit here; let refresh_options do the first edit so the select has options
        await picker.refresh_options(interaction)

    @discord.ui.button(label="Take Reward", style=discord.ButtonStyle.secondary, row=1)
    async def btn_take_reward(self, interaction: Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        picker = RewardPicker(self.author_id, self.target, mode="take")
        await picker.refresh_options(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.gray, row=2)
    async def btn_close(self, interaction: Interaction, _: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Closed.", view=self)

# ---------- Cog ----------
class ModPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    mod = app_commands.Group(
        name="mod",
        description="Moderator tools (points & rewards).",
        guild_only=True,
    )

    @admin_or_mod_check()
    @mod.command(name="panel", description="Open the moderator panel for a member.")
    @app_commands.describe(user="Target member")
    async def panel(self, interaction: Interaction, user: Member):
        view = ActionMenu(author_id=interaction.user.id, target=user)
        await interaction.response.send_message(
            content=f"**Target:** {user.mention}",
            view=view,
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(ModPanel(bot))
