# bot/cogs/user/event_cog.py
import discord
from discord.ext import commands
from discord import app_commands

# Services
from bot.services.events_service import list_user_browseable_events, get_event_message_refs_dto

# Presentation
from bot.presentation.events_presentation import make_event_options, event_default_fmt, make_event_message_vm

# UI
from bot.ui.user.events_views import make_user_event_select_view, UserEventButtons
from bot.ui.user.report_action_views import make_event_select_view

class EventCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="event", description="Browse current events.")
    async def view_event(self, interaction: discord.Interaction):
        """
        Shows a select of browseable events. On selection, we edit the same
        ephemeral to mirror the event's original message and swap in buttons.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        async def render_list(cb_inter: discord.Interaction, *, initial: bool):
            # Build options
            dtos = list_user_browseable_events(limit=25)
            vms = make_event_options(dtos, fmt=event_default_fmt)
            if not vms:
                if initial:
                    await cb_inter.followup.send("There are no events to show right now.", ephemeral=True)
                else:
                    await cb_inter.response.edit_message(
                        content="There are no events to show right now.",
                        embeds=[], attachments=[], view=None
                    )
                return

            view = make_user_event_select_view(vms, on_event_selected)

            if initial:
                await cb_inter.followup.send("Select an event to view:", view=view, ephemeral=True)
            else:
                await cb_inter.response.edit_message(
                    content="Select an event to view:",
                    embeds=[], attachments=[], view=view
                )

        async def on_event_selected(cb_inter: discord.Interaction, event_key: str):            
            refs = get_event_message_refs_dto(event_key)
            if not refs:
                await cb_inter.response.send_message("❌ Event not found anymore.", ephemeral=True)
                return

            vm = make_event_message_vm(refs, guild_id=cb_inter.guild.id)
            
            try:
                channel = cb_inter.guild.get_channel(int(vm.channel_id)) or \
                          await cb_inter.client.fetch_channel(int(vm.channel_id))
                message = await channel.fetch_message(int(vm.message_id))
            except Exception as e:
                print(f"⚠️ Failed to fetch event message: {e}")
                await cb_inter.response.send_message("❌ Could not retrieve the event message.", ephemeral=True)
                return

            files = [await a.to_file() for a in message.attachments[:10] if a]

            content = f"**{vm.title}**"
            if message.content and message.content.strip():
                content += f"\n{message.content.strip()}"

            buttons = UserEventButtons(
                guild_id=cb_inter.guild.id,
                back_to_list=lambda i: render_list(i, initial=False),
            )

            # Edit the existing ephemeral (replace select with buttons)
            try:
                await cb_inter.response.edit_message(
                    content=content,
                    embeds=message.embeds[:10],
                    attachments=files if files else [],
                    view=buttons,
                )
            except Exception as e:
                print(f"⚠️ Edit failed: {e}")
                try:
                    await cb_inter.edit_original_response(
                        content=content,
                        embeds=message.embeds[:10],
                        attachments=files if files else [],
                        view=buttons,
                    )
                except Exception as e2:
                    print(f"⚠️ edit_original_response failed: {e2}")
                    await cb_inter.followup.send(
                        content=content,
                        embeds=message.embeds[:10],
                        view=buttons,
                        ephemeral=True,
                    )

        # Initial render (send, not edit)
        await render_list(interaction, initial=True)
        

    @app_commands.command(name="report_action", description="Report an action for an event.")
    async def report_action(self, interaction: discord.Interaction):
        view = make_event_select_view(interaction.user.id)
        if view is None:
            await interaction.response.send_message("⚠️ No events available right now.", ephemeral=True)
            return
    
        await interaction.response.send_message(
            "🎯 Select the event first:",
            view=view,
            ephemeral=True
        )
    

async def setup(bot: commands.Bot):
    await bot.add_cog(EventCog(bot))