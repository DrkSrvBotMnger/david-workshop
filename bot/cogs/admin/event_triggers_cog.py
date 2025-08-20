import discord
from discord.ext import commands
from discord import app_commands

from bot.utils.time_parse_paginate import admin_or_mod_check
from bot.presentation.event_triggers_presentation import (
    make_event_options, make_trigger_type_options, make_prompt_options, make_ae_options
)
from bot.ui.common.selects import GenericSelectView
from bot.ui.admin.event_triggers_views import ConfigModal, EventFilterAndSelectView, TriggerTypeSelectView
from bot.services.event_triggers_service import create_event_trigger_service
from bot.services.events_service import get_event_dto_by_id
from bot.utils.discord_helpers import get_trigger_label

EVENT_STATUSES = ["all", "draft", "visible", "active", "archived"]

class AdminEventTriggersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @admin_or_mod_check()
    @app_commands.command(name="admin_event_triggers", description="Create a milestone/trigger reward for an event")
    async def admin_event_triggers(self, interaction: discord.Interaction):
        await self.send_event_select(interaction, selected_status="all", is_first=True)

    async def send_event_select(
        self,
        interaction: discord.Interaction,
        selected_status="all",
        is_first=False,
        is_edit=False
    ):
        status = selected_status if selected_status != "all" else None
        event_options = make_event_options(
            event_type_filter=None,
            status_filter=(status,) if status else None,
        )

        # Inner handler to update the status filter and refresh
        async def on_status_select(inter: discord.Interaction):
            new_status = inter.data["values"][0]
            await self.send_event_select(inter, selected_status=new_status, is_first=False, is_edit=True)

        # Inner handler when the user picks an event
        async def on_event_select(inter: discord.Interaction):
            event_id = inter.data["values"][0]
            if event_id == "none":
                await inter.response.edit_message(content="No events to select.", view=None)
                return
            await self.send_trigger_type_select(inter, event_id)

        view = EventFilterAndSelectView(
            status_options=EVENT_STATUSES,
            selected_status=selected_status,
            event_options=event_options,
            on_status_select=on_status_select,
            on_event_select=on_event_select,
        )

        content = "Filter by status and pick an event to manage triggers:"

        if is_first:
            await interaction.response.send_message(
                content=content,
                view=view,
                ephemeral=True
            )
        elif is_edit:
            await interaction.response.edit_message(
                content=content,
                view=view
            )
        else:
            await interaction.followup.send(
                content=content,
                view=view,
                ephemeral=True
            )

    async def send_trigger_type_select(self, interaction: discord.Interaction, event_id: int):
        event_dto = get_event_dto_by_id(event_id)
        trigger_options = make_trigger_type_options(event_dto.event_type)

        async def on_trigger_selected(inter: discord.Interaction):
            trigger_type = inter.data["values"][0]
            if trigger_type == "prompt_repeat":
                await self.send_prompt_select(inter, event_id, trigger_type)
            elif trigger_type == "action_repeat":
                await self.send_ae_select(inter, event_id, trigger_type)
            else:
                await self.send_config_modal(interaction= inter, event_id= event_id, trigger_type=trigger_type, prefill=None)

        view = TriggerTypeSelectView(trigger_options, on_trigger_selected)

        await interaction.response.edit_message(
            content=f"**Event:** {event_dto.event_name}\nNow choose a trigger type:",
            view=view
        )

    async def send_prompt_select(self, interaction: discord.Interaction, event_id: int, trigger_type: str):
        prompt_options = make_prompt_options(event_id)
        
        if prompt_options[0].value == "none":
            await interaction.response.send_message("⚠️ No prompts found for this event.", ephemeral=True)
            return
        
        async def on_prompt_selected(inter: discord.Interaction, prompt_code: str):
            prompt_code = inter.data["values"][0]
            prefill = {"prompt_code": prompt_code}
            await self.send_config_modal(inter, event_id, trigger_type, prefill)
    
        view = GenericSelectView(
            options=prompt_options,
            on_select=on_prompt_selected,
            placeholder="Select a prompt"
        )
        await interaction.response.edit_message(
            content="Select the prompt this trigger applies to:",
            view=view
        )
    
    async def send_ae_select(self, interaction: discord.Interaction, event_id: int, trigger_type: str):    
        ae_options = make_ae_options(event_id)
        
        if ae_options[0].value == "none":
            await interaction.response.send_message("⚠️ No action-events found for this event.", ephemeral=True)
            return

        async def on_ae_selected(inter: discord.Interaction, action_event_id: str):
            action_event_id = inter.data["values"][0]
            prefill = {"action_event_id": int(action_event_id)}
            await self.send_config_modal(inter, event_id, trigger_type, prefill)
            
        view = GenericSelectView(
            options=ae_options,
            on_select=on_ae_selected,
            placeholder="Select an action"
        )
        await interaction.response.edit_message(
            content="Select the action this trigger applies to:",
            view=view
        )
    
    async def send_config_modal(self, interaction: discord.Interaction, event_id: int, trigger_type: str, prefill: dict | None):
        modal = ConfigModal(trigger_type, prefill)
        await interaction.response.send_modal(modal)
        await modal.wait()
        config = modal.get_config()
        await self.create_trigger(interaction, event_id, trigger_type, config)

    async def create_trigger(self, interaction: discord.Interaction, event_id: int, trigger_type: str, config: dict):
        create_data = {
            "event_id": event_id,
            "trigger_type": trigger_type,
            "config": config
        }
        try:
            trigger_dto = create_event_trigger_service(create_data)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        
        event_dto = get_event_dto_by_id(event_id)
        await interaction.followup.send(
            f"✅ Trigger created for **{event_dto.event_name}**!\n"
            f"• **Type:** {get_trigger_label(trigger_type)}\n"
            f"• **Config:** `{config}`\n"
            f"• *(No reward yet — use `/admin_links_reward_event` to link)*",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminEventTriggersCog(bot))