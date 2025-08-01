import discord
import json
from discord import app_commands
from discord.ext import commands
from typing import Optional
from bot.crud.actions_crud import create_action as crud_create_action, get_action_by_key, get_all_actions
from bot.crud.users_crud import action_is_used
from bot.config import ALLOWED_ACTION_INPUT_FIELDS, ACTIONS_PER_PAGE
from bot.utils import admin_or_mod_check, paginate_embeds, now_iso
from db.database import db_session


class AdminActionCommands(commands.GroupCog, name="admin_action"):
    """Admin commands for managing actions."""

    def __init__(self, bot):
        self.bot = bot

    # === CREATE ACTION ===
    @admin_or_mod_check()
    @app_commands.command(name="create", description="Create a new global action type.")
    @app_commands.describe(
        action_key="Short unique key for the action (lowercase, underscores only, e.g. submit_fic)",
        description="Description of what this action is for",
        input_fields=f"Optional: comma-separated list of allowed fields ({', '.join(ALLOWED_ACTION_INPUT_FIELDS)})"
    )
    async def create_action(
        self,
        interaction: discord.Interaction,
        action_key: str,
        description: str,
        input_fields: str = ""
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # --- Validate action key format ---
        if not action_key.isidentifier() or not action_key.islower():
            await interaction.followup.send(
                "❌ Action key must be lowercase letters, numbers, and underscores only (e.g. `submit_fic`)."
            )
            return

        # --- Parse and validate input fields ---
        input_fields_json = None
        if input_fields.strip():
            parsed = [f.strip() for f in input_fields.split(",") if f.strip()]
            for field in parsed:
                if field not in ALLOWED_ACTION_INPUT_FIELDS:
                    await interaction.followup.send(
                        f"❌ Invalid input field `{field}`. Allowed values: {', '.join(ALLOWED_ACTION_INPUT_FIELDS)}"
                    )
                    return
            input_fields_json = json.dumps(parsed)

        # --- Check for duplicate ---
        with db_session() as session:
            if get_action_by_key(session, action_key):
                await interaction.followup.send(f"❌ Action `{action_key}` already exists.")
                return

            # --- Create the action ---
            crud_create_action(
                session=session,
                action_key=action_key,
                description=description,
                input_fields_json=input_fields_json
            )

        # --- Confirmation ---
        await interaction.followup.send(
            f"✅ **Action Created**\n"
            f"**Key:** `{action_key}`\n"
            f"**Description:** {description}\n"
            f"**Input fields:** {', '.join(json.loads(input_fields_json)) if input_fields_json else 'None'}"
        )


    # === DELETE ACTION ===
    @admin_or_mod_check()
    @app_commands.describe(action_key="The key of the action to delete")
    @app_commands.command(name="delete", description="Delete a global action type (if unused and active).")
    async def delete_action(self, interaction: discord.Interaction, action_key: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            action = get_action_by_key(session, action_key)
            if not action:
                await interaction.followup.send(
                    f"❌ Action `{action_key}` does not exist."
                )
                return

            # Block if inactive
            if not action.active:
                await interaction.followup.send(
                    f"❌ Action `{action_key}` is inactive. You cannot delete historical actions."
                )
                return

            # Block if referenced in UserAction
            if action_is_used(session, action.id):
                await interaction.followup.send(
                    f"❌ Action `{action_key}` is referenced in user history and cannot be deleted.\n"
                    f"Deactivate it instead to keep history intact."
                )
                return

            # Delete it
            session.delete(action)

        await interaction.followup.send(f"🗑️ Action `{action_key}` deleted successfully.")


    # === DEACTIVATE ACTION ===
    @admin_or_mod_check()
    @app_commands.command(name="deactivate", description="Mark an action as inactive and version its key.")
    @app_commands.describe(
        action_key="The key of the action to deactivate (will be versioned)"
    )
    async def deactivate_action(self, interaction: discord.Interaction, action_key: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            action = get_action_by_key(session, action_key)
            if not action:
                await interaction.followup.send(f"❌ Action `{action_key}` does not exist.")
                return
            if not action.active:
                await interaction.followup.send(f"⚠️ Action `{action_key}` is already inactive.")
                return

            # Auto-version key: find next available `_vX`
            base_key = action_key
            version = 1
            while True:
                candidate_key = f"{base_key}_v{version}"
                if not get_action_by_key(session, candidate_key):
                    break
                version += 1

            # Update record
            action.action_key = candidate_key
            action.active = False
            action.deactivated_at = now_iso()

        await interaction.followup.send(
            f"✅ Action `{action_key}` has been deactivated and renamed to `{candidate_key}`.\n"
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
            actions = get_all_actions(
                session,
                active=None if show_inactive else True,
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
    
                desc = action.description or "No description"
                if len(desc) > 1000:
                    desc = desc[:1000] + "…"
    
                parsed_actions.append({
                    "key": action.action_key,
                    "desc": desc,
                    "input_fields": input_fields,
                    "active": action.active
                })
    
        if not parsed_actions:
            await interaction.followup.send("ℹ️ No actions found with the current filters.", ephemeral=True)
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
