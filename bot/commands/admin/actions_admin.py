import discord
import json
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from bot.utils import admin_or_mod_check, paginate_embeds
from db.database import db_session
from bot.crud.actions_crud import create_action as crud_create_action, get_action_by_key, get_all_actions
from bot.config import ALLOWED_ACTION_INPUT_FIELDS


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
        default_self_reportable="Can users self-report this action by default? (true/false)",
        input_fields=f"Optional: comma-separated list of allowed fields ({', '.join(ALLOWED_ACTION_INPUT_FIELDS)})"
    )
    async def create_action(
        self,
        interaction: discord.Interaction,
        action_key: str,
        description: str,
        default_self_reportable: bool = True,
        input_fields: str = ""
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # --- Validate action key format ---
        if not action_key.isidentifier() or not action_key.islower():
            await interaction.followup.send(
                "❌ Action key must be lowercase letters, numbers, and underscores only (e.g. `submit_fic`).",
                ephemeral=True
            )
            return

        # --- Parse and validate input fields ---
        input_fields_json = None
        if input_fields.strip():
            parsed = [f.strip() for f in input_fields.split(",") if f.strip()]
            for field in parsed:
                if field not in ALLOWED_ACTION_INPUT_FIELDS:
                    await interaction.followup.send(
                        f"❌ Invalid input field `{field}`. Allowed values: {', '.join(ALLOWED_ACTION_INPUT_FIELDS)}",
                        ephemeral=True
                    )
                    return
            input_fields_json = json.dumps(parsed)

        # --- Check for duplicate ---
        with db_session() as session:
            if get_action_by_key(session, action_key):
                await interaction.followup.send(f"❌ Action `{action_key}` already exists.", ephemeral=True)
                return

            # --- Create the action ---
            crud_create_action(
                session=session,
                action_key=action_key,
                description=description,
                default_self_reportable=default_self_reportable,
                input_fields_json=input_fields_json
            )

        # --- Confirmation ---
        await interaction.followup.send(
            f"✅ **Action Created**\n"
            f"**Key:** `{action_key}`\n"
            f"**Description:** {description}\n"
            f"**Self-reportable:** {'Yes' if default_self_reportable else 'No'}\n"
            f"**Input fields:** {', '.join(json.loads(input_fields_json)) if input_fields_json else 'None'}",
            ephemeral=True
        )


    # === DELETE ACTION ===
    @admin_or_mod_check()
    @app_commands.command(name="delete", description="Delete a global action type.")
    @app_commands.describe(
        action_key="The unique key of the action to delete (e.g. submit_fic)"
    )
    async def delete_action(self, interaction: discord.Interaction, action_key: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        # --- Check if action exists ---
        from bot.crud.actions_crud import get_action_by_key, delete_action as crud_delete_action
    
        with db_session() as session:
            action = get_action_by_key(session, action_key)
            if not action:
                await interaction.followup.send(
                    f"❌ Action `{action_key}` does not exist.",
                    ephemeral=True
                )
                return
    
            # --- Delete action ---
            crud_delete_action(session, action_key)
    
        # --- Confirmation ---
        await interaction.followup.send(
            f"🗑️ Action `{action_key}` deleted successfully.",
            ephemeral=True
        )
    

    # === LIST ACTIONS ===
    @admin_or_mod_check()
    @app_commands.command(name="list", description="List all available global actions.")
    async def list_actions(self, interaction: discord.Interaction):
        print(f"listactions callback fired from: {__file__}")
        print("1️⃣ Starting list_actions_cmd")
    
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        # Icons for input field types
        FIELD_ICONS = {
            "url": "🌐",
            "numeric_value": "🔢",
            "text_value": "📝",
            "boolean_value": "✔️/❌",
            "date_value": "📅"
        }
    
        # Extract data before session closes
        with db_session() as session:
            actions = get_all_actions(session)
            parsed_actions = []
    
            for action in actions:
                try:
                    input_fields = json.loads(action.input_fields_json) if action.input_fields_json else []
                except Exception as e:
                    print(f"ERROR: Failed to parse input_fields for {action.action_key}: {e}")
                    input_fields = []
    
                # Truncate description if too long
                desc = action.description or "No description"
                if len(desc) > 1000:
                    desc = desc[:1000] + "…"
    
                parsed_actions.append({
                    "key": action.action_key,
                    "desc": desc,
                    "self_report": action.default_self_reportable,
                    "input_fields": input_fields
                })
    
        if not parsed_actions:
            await interaction.followup.send("ℹ️ No actions are currently defined.", ephemeral=True)
            return
    
        # Build embeds (paginate if more than 25)
        embeds = []
        for i in range(0, len(parsed_actions), 25):
            chunk = parsed_actions[i:i + 25]
    
            embed = discord.Embed(
                title="📋 Available Global Actions",
                description="Use the **Action Key** when linking to an event.",
                color=discord.Color.blue()
            )
    
            for action in chunk:
                # Convert fields to icons
                icon_list = [
                    f"{FIELD_ICONS.get(field, '❓')} {field}" for field in action["input_fields"]
                ]
                input_fields_str = ", ".join(icon_list) if icon_list else "None"
    
                value = (
                    f"📜 {action['desc']}\n"
                    f"👤 Self‑reportable: {'✅' if action['self_report'] else '❌'}\n"
                    f"📦 Input fields: {input_fields_str}"
                )
    
                embed.add_field(
                    name=f"🆔 `{action['key']}`",
                    value=value,
                    inline=False
                )
    
            embeds.append(embed)
    
        # Send paginated if needed
        if len(embeds) > 1:
            await paginate_embeds(interaction, embeds)
        else:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
    
        print("2️⃣ Done listing actions.")

    

async def setup(bot):
    await bot.add_cog(AdminActionCommands(bot))
