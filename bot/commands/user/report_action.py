from __future__ import annotations

import json
import re
import discord
from discord import app_commands, Interaction
from discord.ext import commands

from db.database import db_session
from db.schema import (
    User, Event, Action, ActionEvent, RewardEvent, Reward, Inventory, UserAction, UserEventData
)
from bot.crud import users_crud
from bot.utils.time_parse_paginate import now_iso, parse_required_fields, parse_help_texts


# -----------------------------
# Helpers
# -----------------------------


def get_self_reportable_action_events(session):
    """
    Returns list of tuples (ae, action, event, revent) where:
    - action is active
    - ae.is_self_reportable = True
    - event is active OR (visible AND ae.is_allowed_during_visible)
    """
    q = (
        session.query(ActionEvent, Action, Event, RewardEvent)
        .join(Action, ActionEvent.action_id == Action.id)
        .join(Event, ActionEvent.event_id == Event.id)
        .outerjoin(RewardEvent, RewardEvent.id == ActionEvent.reward_event_id)
        .filter(Action.is_active == True)
        .filter(ActionEvent.is_self_reportable == True)
    )
    rows = []
    for ae, action, event, revent in q.all():
        status = getattr(event.event_status, "name", str(event.event_status))
        if status == "active" or (status == "visible" and bool(ae.is_allowed_during_visible)):
            rows.append((ae, action, event, revent))
    return rows


# -----------------------------
# Dynamic Modal for any combination of fields (max 5 inputs)
# -----------------------------

class DynamicReportModal(discord.ui.Modal, title="Report action"):
    def __init__(self, action_event_id: int, fields: list[str], help_map: dict[str, str] | None = None):
        super().__init__(timeout=180)
        self.action_event_id = action_event_id
        self.fields = fields
        self.help_map = help_map or {}
        self.inputs: dict[str, discord.ui.TextInput] = {}

        # Helper to pick a placeholder: field-specific help if any, else a sane default
        def ph(field: str, default: str) -> str:
            txt = self.help_map.get(field, "").strip()
            return txt if txt else default

        if "url" in fields:
            ti = discord.ui.TextInput(
                label="Link (URL)",
                placeholder=ph("url", "https://…"),
                style=discord.TextStyle.short,
                required=True
            )
            self.inputs["url"] = ti
            self.add_item(ti)

        if "numeric_value" in fields:
            ti = discord.ui.TextInput(
                label="Number",
                placeholder=ph("numeric_value", "e.g., 5"),
                style=discord.TextStyle.short,
                required=True
            )
            self.inputs["numeric_value"] = ti
            self.add_item(ti)

        if "text_value" in fields:
            ti = discord.ui.TextInput(
                label="Notes / details",
                placeholder=ph("text_value", "Add any relevant details…"),
                style=discord.TextStyle.paragraph,
                required=True
            )
            self.inputs["text_value"] = ti
            self.add_item(ti)

        if "boolean_value" in fields:
            ti = discord.ui.TextInput(
                label="Yes / No",
                placeholder=ph("boolean_value", "yes or no"),
                style=discord.TextStyle.short,
                required=True
            )
            self.inputs["boolean_value"] = ti
            self.add_item(ti)

        if "date_value" in fields:
            ti = discord.ui.TextInput(
                label="Date",
                placeholder=ph("date_value", "YYYY-MM-DD"),
                style=discord.TextStyle.short,
                required=True
            )
            self.inputs["date_value"] = ti
            self.add_item(ti)


    async def on_submit(self, interaction: Interaction):
        # Validate & normalize
        data = {
            "url": None,
            "numeric": None,
            "text": None,
            "boolean": None,
            "date": None,
        }

        if "url" in self.fields:
            v = str(self.inputs["url"].value).strip()
            if not (v.startswith("http://") or v.startswith("https://")):
                await interaction.response.send_message("⚠️ Please enter a valid URL (http/https).", ephemeral=True)
                return
            data["url"] = v

        if "numeric_value" in self.fields:
            raw = str(self.inputs["numeric_value"].value).strip()
            try:
                n = int(raw)
                if n < 0:
                    raise ValueError()
            except Exception:
                await interaction.response.send_message("⚠️ Number must be an integer ≥ 0.", ephemeral=True)
                return
            data["numeric"] = n

        if "text_value" in self.fields:
            data["text"] = str(self.inputs["text_value"].value).strip()

        if "boolean_value" in self.fields:
            raw = str(self.inputs["boolean_value"].value).strip().lower()
            if raw in {"yes", "y", "true", "1"}:
                data["boolean"] = True
            elif raw in {"no", "n", "false", "0"}:
                data["boolean"] = False
            else:
                await interaction.response.send_message("⚠️ For Yes/No, enter yes or no.", ephemeral=True)
                return

        if "date_value" in self.fields:
            raw = str(self.inputs["date_value"].value).strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
                await interaction.response.send_message("⚠️ Date must be YYYY-MM-DD.", ephemeral=True)
                return
            data["date"] = raw

        await handle_action_submission(
            interaction,
            self.action_event_id,
            url=data["url"],
            numeric=data["numeric"],
            text=data["text"],
            boolean=data["boolean"],
            date=data["date"]
        )

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


# -----------------------------
# Select View
# -----------------------------

class ActionEventSelect(discord.ui.Select):
    def __init__(self, options_data: list[dict]):
        """
        Each item in options_data must contain:
          - value: str(ActionEvent.id)
          - label: str (<=100)
          - description: str (<=100)  # uses general help
          - fields: list[str]
          - help_map: dict[str, str]  # includes 'general' and per-field helps
        """
        opts = [
            discord.SelectOption(
                label=o["label"][:100],
                value=o["value"],
                description=(o.get("description") or "")[:100]
            ) for o in options_data[:25]
        ]
        super().__init__(
            placeholder="Choose an action to report…",
            min_values=1,
            max_values=1,
            options=opts,
            custom_id="report_action_select"
        )
        # Keep a tiny payload map in memory for the callback
        self._payload = {o["value"]: o for o in options_data}

    async def callback(self, interaction: Interaction):
        payload = self._payload[self.values[0]]
        action_event_id = int(payload["value"])
        fields = payload.get("fields", [])
        help_map = payload.get("help_map", {})  # <— dict
    
        if not fields:
            await handle_action_submission(
                interaction,
                action_event_id,
                url=None, numeric=None, text=None, boolean=None, date=None
            )
            return
    
        modal = DynamicReportModal(action_event_id, fields, help_map)
        await interaction.response.send_modal(modal)


class ActionEventView(discord.ui.View):
    def __init__(self, options_data: list[dict], *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(ActionEventSelect(options_data))


# -----------------------------
# Core submission handler
# -----------------------------

async def handle_action_submission(
    interaction: Interaction,
    action_event_id: int,
    *,
    url: str | None,
    numeric: int | None,
    text: str | None,
    boolean: bool | None,
    date: str | None
):
    # Fresh session here
    with db_session() as session:
        ae = session.query(ActionEvent).get(action_event_id)
        if not ae:
            await interaction.response.send_message("❌ Action config not found anymore.", ephemeral=True)
            return

        action = ae.action
        event = ae.event

        # Availability checks
        if not action.is_active:
            await interaction.response.send_message("⚠️ This action is not active.", ephemeral=True)
            return

        status = getattr(event.event_status, "name", str(event.event_status))
        is_open = (status == "active") or (status == "visible" and bool(ae.is_allowed_during_visible))
        if not is_open:
            await interaction.response.send_message("⚠️ This action isn’t available right now.", ephemeral=True)
            return

        # User
        user = users_crud.get_or_create_user(session, interaction.user)

        # Record action
        ua = UserAction(
            user_id=user.id,
            action_event_id=ae.id,   # <- new
            event_id=event.id,
            created_by=str(interaction.user.id),
            created_at=now_iso(),
            url=url,
            numeric_value=numeric,
            text_value=text,
            boolean_value=boolean,
            date_value=date,
        )
        session.add(ua)

        # --- Points calculation
        base = ae.points_granted or 0
        points = base

        # NEW: scale by numeric input when present
        if numeric is not None:
            points = base * numeric

        if points:
            user.points += points
            user.total_earned += points

            ued = (
                session.query(UserEventData)
                .filter(
                    UserEventData.user_id == user.id,
                    UserEventData.event_id == event.id
                )
                .first()
            )
            if not ued:
                ued = UserEventData(
                    user_id=user.id,
                    event_id=event.id,
                    points_earned=0,
                    joined_at=now_iso(),
                    created_by=str(interaction.user.id)
                )
                session.add(ued)
            ued.points_earned += points

        # Optional reward
        granted_reward_msg = ""
        if ae.reward_event_id:
            revent = session.query(RewardEvent).get(ae.reward_event_id)
            if revent:
                reward = session.query(Reward).get(revent.reward_id)
                if reward:
                    inv = (
                        session.query(Inventory)
                        .filter(Inventory.user_id == user.id, Inventory.reward_id == reward.id)
                        .first()
                    )
                    if inv:
                        # For non-stackables, keep quantity as-is; stackables can increment
                        if reward.is_stackable:
                            inv.quantity += 1
                    else:
                        inv = Inventory(user_id=user.id, reward_id=reward.id, quantity=1)
                        session.add(inv)
                    reward.number_granted += 1
                    granted_reward_msg = f"\n🎁 You received **{reward.reward_name}**."

        session.commit()

    earned_txt = f"⭐ +{points} points" if points else "No points for this action"
    await interaction.response.send_message(f"✅ Reported! {earned_txt}.{granted_reward_msg}", ephemeral=True)


# -----------------------------
# Cog
# -----------------------------

class UserActions(commands.Cog):
    """User-facing self-report command with dynamic modal inputs."""
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="report_action", description="Report a self-reportable action")
    async def report_action(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            rows = get_self_reportable_action_events(session)

            user = users_crud.get_or_create_user(session, interaction.user)
            filtered_rows = []
            for ae, action, event, revent in rows:
                if not ae.is_repeatable:
                    already = (
                        session.query(UserAction.id)
                        .filter(
                            UserAction.user_id == user.id,
                            UserAction.action_event_id == ae.id
                        )
                        .first()
                    )
                    if already:
                        continue  # skip already completed non-repeatables
                filtered_rows.append((ae, action, event, revent))

            if not filtered_rows:
                await interaction.followup.send(
                    "There are no self-reportable actions available right now.",
                    ephemeral=True
                )
                return

            options: list[dict] = []
            for ae, action, event, revent in filtered_rows:
                fields = parse_required_fields(action.input_fields_json)
                help_map = parse_help_texts(ae.input_help_text, fields)

                label =f"{event.event_name} • {action.action_description} ({ae.variant})"
                general = (help_map.get("general") or "").strip()
                print(f"general {general}")
                desc = general[:100] or "Report this action"
        
                options.append({
                    "label": label,
                    "value": str(ae.id),
                    "description": desc,
                    "fields": fields,
                    "help_map": help_map,
                })

        view = ActionEventView(options)
        await interaction.followup.send("Select an action to report:", view=view, ephemeral=True)


# Setup function for cogs loader
async def setup(bot: commands.Bot):
    await bot.add_cog(UserActions(bot))
