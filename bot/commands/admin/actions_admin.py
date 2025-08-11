import discord
import json
import re
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
from bot.crud import actions_crud, action_events_crud
from bot.crud.users_crud import ae_is_used_by_action_id
from bot.config import ALLOWED_ACTION_INPUT_FIELDS, ACTIONS_PER_PAGE
from bot.utils.time_parse_paginate import admin_or_mod_check, paginate_embeds, now_iso
from db.database import db_session
from db.schema import Action, ActionEvent



# --- HELPERS ---

SHORTCODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

def validate_shortcode(shortcode: str) -> Optional[str]:
    """Return error message if invalid, else None."""
    if not SHORTCODE_RE.match(shortcode or ""):
        return ("❌ Action key must start with a letter and contain only lowercase letters, "
                "numbers, and underscores (e.g. 'submit_fic').")
    if len(shortcode) > 64:
        return "❌ Action key is too long (max 64 characters)."
    return None

def normalize_fields(selected: List[str]) -> List[str]:
    """Always return ['general', ...unique valid selections in given order]."""
    seen = set()
    cleaned = ["general"]
    for f in selected:
        if f in ALLOWED_ACTION_INPUT_FIELDS and f not in seen:
            seen.add(f)
            cleaned.append(f)
    # must have at least one after filtering
    if not cleaned:
        return []
    return ["general"]




# --- UI: MODAL TO CAPTURE SHORTCODE + DESCRIPTION ---

class CreateActionModal(discord.ui.Modal, title="Create Action"):
    shortcode = discord.ui.TextInput(
        label="Action key (For example submit_fic)",
        placeholder="lowercase_with_underscores",
        min_length=3,
        max_length=64
    )
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.paragraph,
        placeholder="What is this action for?",
        min_length=5,
        max_length=100
    )

    def __init__(self, cog: "AdminActionCommands"):
        super().__init__()
        self.cog = cog
        self._shortcode: Optional[str] = None
        self._description: Optional[str] = None

    async def on_submit(self, interaction: discord.Interaction):
        sc = str(self.shortcode.value).strip().lower()  # normalize
        err = validate_shortcode(sc)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        with db_session() as session:
            if actions_crud.get_action_by_key(session=session, action_key=sc):
                await interaction.response.send_message(f"❌ Action `{sc}` already exists.", ephemeral=True)
                return
        self._shortcode = sc
        self._description = str(self.description.value).strip()
    
        view = FieldSelectView(cog=self.cog, shortcode=self._shortcode, description=self._description)
        await interaction.response.send_message(
            "Select at least **one** input field. ‘general’ is added automatically.",
            view=view,
            ephemeral=True
        )




# --- UI: FIELD MULTI-SELECT + CONFIRM ---
class FieldMultiSelect(discord.ui.Select):
    def __init__(self, options, parent: "FieldSelectView", row: int = 0):
        super().__init__(
            placeholder="Choose input fields…",
            min_values=0,
            max_values=len(options),
            options=[discord.SelectOption(label=f, value=f) for f in options],
            row=row,
        )
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent._last_selection = list(self.values)
        await interaction.response.defer()  # prevent “This interaction failed”


class FieldSelectView(discord.ui.View):
    def __init__(self, cog: "AdminActionCommands", shortcode: str, description: str, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.shortcode = shortcode
        self.description = description
        self._last_selection: List[str] = []

        # force rows: select on row 0, buttons on row 1
        self.add_item(FieldMultiSelect(options=ALLOWED_ACTION_INPUT_FIELDS, parent=self, row=0))

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected = self._last_selection  # kept up-to-date by FieldMultiSelect.callback
        fields = normalize_fields(selected)
        if not fields:
            await interaction.response.send_message(
                "❌ You must select at least one valid input field.", ephemeral=True
            )
            return

        input_fields_json = json.dumps(fields)
        with db_session() as session:
            if actions_crud.get_action_by_key(session=session, action_key=self.shortcode):
                await interaction.response.send_message(f"❌ Action `{self.shortcode}` already exists.", ephemeral=True)
                return

            actions_crud.create_action(
                session=session,
                action_create_data={
                    "action_key": self.shortcode,
                    "action_description": self.description,
                    "input_fields_json": input_fields_json
                }
            )

        await interaction.response.edit_message(
            content=(
                "✅ **Action Created**\n"
                f"**Key:** `{self.shortcode}`\n"
                f"**Description:** {self.description}\n"
                f"**Input fields:** {', '.join(fields)}"
            ),
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❎ Creation cancelled.", view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True




class AdminActionCommands(commands.GroupCog, name="admin_action"):
    """Admin commands for managing actions."""

    def __init__(self, bot):
        self.bot = bot

    
    # === CREATE ACTION ===
    @admin_or_mod_check()
    @app_commands.command(name="create", description="Create a new global action type.")
    async def create_action(self, interaction: discord.Interaction):
        """Open a modal, then a select view to configure the action cleanly."""
        await interaction.response.send_modal(CreateActionModal(self))


    # === DELETE ACTION ===
    @admin_or_mod_check()
    @app_commands.describe(shortcode="Shortcode of the action to delete")
    @app_commands.command(
        name="delete",
        description="Delete a global action type (if unused and active)."
    )
    async def delete_action(self, interaction: discord.Interaction, shortcode: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            action = actions_crud.get_action_by_key(session, shortcode)
            if not action:
                await interaction.followup.send(f"❌ Action `{shortcode}` does not exist.")
                return

            # Business rule: don’t allow deleting inactive actions (history retention)
            if not action.is_active:
                await interaction.followup.send(
                    f"❌ Action `{shortcode}` is inactive. You cannot delete historical actions."
                )
                return

            # Block if any user history exists for this action
            if ae_is_used_by_action_id(session, action.id):
                await interaction.followup.send(
                    f"❌ Action `{shortcode}` is referenced in user history and cannot be deleted.\n"
                    f"Deactivate it instead to keep history intact."
                )
                return

            # Collect all ActionEvent configs for this Action
            aes = (
                session.query(ActionEvent)
                .filter(ActionEvent.action_id == action.id)
                .all()
            )

            # Delete each ActionEvent via CRUD so it gets logged
            performed_by = str(interaction.user.id)
            performed_at = now_iso()
            deleted_configs = 0

            for ae in aes:
                ok = action_events_crud.delete_action_event(
                    session=session,
                    action_event_key=ae.action_event_key,
                    performed_by=performed_by,
                    performed_at=performed_at,
                    force=False,  # flip to True if you want to force logging
                )
                if ok:
                    deleted_configs += 1

            # Finally delete the Action itself (simple CRUD delete)
            deleted = actions_crud.delete_action(session=session, action_key=shortcode)
            if not deleted:
                await interaction.edit_original_response(content="❌ Action deletion failed unexpectedly.", view=None)
                return

        await interaction.followup.send(
            f"🗑️ Action `{shortcode}` deleted successfully "
            f"(removed {deleted_configs} configuration(s))."
        )


    # === DEACTIVATE ACTION ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="The key of the action to deactivate (will be versioned)"
    )
    @app_commands.command(name="deactivate", description="Mark an action as inactive and version its key.")
    async def deactivate_action(
        self, 
        interaction: discord.Interaction, 
        shortcode: str
    ):
        
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            action = actions_crud.get_action_by_key(session, shortcode)
            if not action:
                await interaction.followup.send(f"❌ Action `{shortcode}` does not exist.")
                return
            if not action.is_active:
                await interaction.followup.send(f"⚠️ Action `{shortcode}` is already inactive.")
                return

            # Auto-version key: find next available `_vX`
            base_key = shortcode
            version = 1
            while True:
                candidate_key = f"{base_key}_v{version}"
                if not actions_crud.get_action_by_key(session, candidate_key):
                    break
                version += 1

            action_create_data ={
                "action_key": candidate_key,
                "is_active": False
            }
            
            action = actions_crud.deactivate_action (
                session=session,
                action_key=shortcode,
                action_update_data=action_create_data
            )

        await interaction.followup.send(
            f"✅ Action `{shortcode}` has been deactivated and renamed to `{candidate_key}`.\n"
            f"It will no longer be available for linking to new events."
        )

    
    # === LIST ACTIONS ===
    @admin_or_mod_check()
    @app_commands.describe(
        show_inactive="Set to True to show inactive actions",
        search_key="Search actions by key (partial match)"
    )
    @app_commands.command(name="list", description="List all available global actions.")
    async def list_actions(
        self,
        interaction: discord.Interaction,
        show_inactive: bool = False,
        search_key: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        # Icons for input field types
        FIELD_ICONS = {
            "url": "🌐",
            "numeric_value": "🔢",
            "text_value": "📝",
            "boolean_value": "✔️/❌",
            "date_value": "📅"
        }
    
        with db_session() as session:
            actions = actions_crud.get_all_actions(
                session=session,
                is_active=None if show_inactive else True,
                key_search=search_key,
                order_by="key"  # alphabetical for UI display
            )
    
            parsed_actions = []
            for action in actions:
                try:
                    input_fields = json.loads(action.input_fields_json) if action.input_fields_json else []
                except Exception as e:
                    print(f"ERROR: Failed to parse input_fields for {action.action_key}: {e}")
                    input_fields = []
    
                desc = action.action_description or "No description"
                if len(desc) > 1000:
                    desc = desc[:1000] + "…"
    
                parsed_actions.append({
                    "key": action.action_key,
                    "desc": desc,
                    "input_fields": input_fields,
                    "active": action.is_active
                })
    
        if not parsed_actions:
            await interaction.followup.send("ℹ️ No actions found with the current filters.")
            return
    
        # Build paginated embeds
        pages = []
        for i in range(0, len(parsed_actions), ACTIONS_PER_PAGE):
            chunk = parsed_actions[i:i + ACTIONS_PER_PAGE]
            description_text = "Use the **Action Key** when linking to an event.\n"
            description_text += "🟢 Active | 🔴 Inactive\n" if show_inactive else ""
            description_text += f"🔍 Search: `{search_key}`" if search_key else "🔍 No search filter"
            embed = discord.Embed(
                title=f"📋 Global Actions ({i+1}-{i+len(chunk)}/{len(parsed_actions)})",
                description=description_text,
                color=discord.Color.blue()
            )
    
            for action in chunk:
                status_icon = "🟢" if action["active"] else "🔴"
                icon_list = [f"{FIELD_ICONS.get(field, '❓')} {field}" for field in action["input_fields"]]
                input_fields_str = ", ".join(icon_list) if icon_list else "None"
    
                value = (
                    f"📜 {action['desc']}\n"
                    f"📦 Input fields: {input_fields_str}"
                )
                if show_inactive:
                    name_display = f"🆔 `{action['key']}` {status_icon}"
                else:
                    name_display = f"🆔 `{action['key']}`"
    
                embed.add_field(name=name_display, value=value, inline=False)
    
            pages.append(embed)
    
        await paginate_embeds(interaction, pages)


async def setup(bot):
    await bot.add_cog(AdminActionCommands(bot))