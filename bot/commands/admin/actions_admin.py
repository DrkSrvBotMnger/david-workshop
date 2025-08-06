import discord
import json
from discord import app_commands
from discord.ext import commands
from typing import Optional
from bot.crud import actions_crud
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
        shortcode="Shortcode for the action (lowercase, underscores only, e.g. submit_fic)",
        description="Description of what this action is for",
        input_fields=f"Optional: comma-separated list of allowed fields ({', '.join(ALLOWED_ACTION_INPUT_FIELDS)})"
    )
    async def create_action(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        description: str,
        input_fields: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # --- Validate action key format ---
        if not shortcode.isidentifier() or not shortcode.islower():
            await interaction.followup.send(
                "❌ Action key must be lowercase letters, numbers, and underscores only (e.g. `submit_fic`)."
            )
            return

        # --- Parse and validate input fields ---
        input_fields_json = None
        if input_fields:
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
            if actions_crud.get_action_by_key(
                session=session, 
                action_key=shortcode
            ):
                await interaction.followup.send(f"❌ Action `{shortcode}` already exists.")
                return

            action_create_data ={
                "action_key": shortcode,
                "action_description": description,
                "input_fields_json": input_fields_json     
            }

            actions_crud.create_action(
                session=session,
                action_create_data=action_create_data
            )

        # --- Confirmation ---
        await interaction.followup.send(
            f"✅ **Action Created**\n"
            f"**Key:** `{shortcode}`\n"
            f"**Description:** {description}\n"
            f"**Input fields:** {', '.join(json.loads(input_fields_json)) if input_fields_json else 'None'}"
        )


    # === DELETE ACTION ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the action to delete"
    )
    @app_commands.command(name="delete", description="Delete a global action type (if unused and active).")
    async def delete_action(
        self, 
        interaction: discord.Interaction, 
        shortcode: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            action = actions_crud.get_action_by_key(session, shortcode)
            if not action:
                await interaction.followup.send(
                    f"❌ Action `{shortcode}` does not exist."
                )
                return

            # Block if inactive
            if not action.is_active:
                await interaction.followup.send(
                    f"❌ Action `{shortcode}` is inactive. You cannot delete historical actions."
                )
                return

            # Block if referenced in UserAction
            if action_is_used(session, action.id):
                await interaction.followup.send(
                    f"❌ Action `{shortcode}` is referenced in user history and cannot be deleted.\n"
                    f"Deactivate it instead to keep history intact."
                )
                return
            
            action = actions_crud.delete_action(
                session,
                action_key=shortcode
            )
            if not action:
            
                await interaction.edit_original_response(content="❌ Event deletion failed unexpectedly.", view=None)
                return

        await interaction.followup.send(f"🗑️ Action `{shortcode}` deleted successfully.")


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