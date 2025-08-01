import discord
from discord import app_commands, Interaction
from discord.ext import commands
from sqlalchemy.exc import IntegrityError
from bot.crud import action_events_crud, reward_events_crud, events_crud
from bot.utils import admin_or_mod_check, paginate_embeds, now_iso
from db.database import db_session
from datetime import datetime


class EventLinksAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin_links = app_commands.Group(
        name="admin_links",
        description="Manage Action-Event and Reward-Event links (Admin only)."
    )

    
    # ========== ACTION EVENT COMMANDS ==========
    # === LINK ACTION EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="link_action_event")
    @app_commands.describe(
        action_id="ID of the action to link",
        event_id="ID of the event to link to",
        input_help_text="Guidance text for input",
        variant="Optional short label to distinguish this variant (e.g., 'current', 'past')",
        points_granted="Optional points to grant for this action in this event",
        reward_event_id="Optional linked reward_event_id",
        self_reportable="Can the user report this action themselves? (default true)"
    )
    async def link_action_event(
        self,
        interaction: Interaction,
        action_id: int,
        event_id: int,,
        input_help_text: str,
        variant: str = None,
        points_granted: int = 0,
        reward_event_id: int = None,
        self_reportable: bool = True
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # 🔹 Normalize and build flavor_key here
        variant_clean = variant.strip().lower().replace(" ", "_") if variant else "default"
        flavor_key = f"{event_id}_{action_id}_{variant_clean}"

        # 🔹 Check if points_granted is non-negative
        if points_granted < 0:
            await interaction.followup.send("❌ Points granted must be 0 or a non-negative number.")

        # 🔹 Check for active event, existing rewards and flavor_key then create action_event
        try:            
            with db_session() as session:

                # Check if event is active
                if events_crud.is_event_active(session, event_id):
                    await interaction.followup.send("❌ Cannot link actions to an active event.")
                    return

                # Check if reward_event_id is valid
                if reward_event_id:
                    reward_event = reward_events_crud.get_reward_event(session, reward_event_id)
                    if not reward_event:
                        await interaction.followup.send(f"❌ RewardEvent `{reward_event_id}` not found.")
                        return

                # Check if flavor_key already exists
                existing_ae = action_events_crud.get_action_event_by_flavor_key(session, flavor_key)
                if existing_ae:
                    await interaction.followup.send(f"❌ An ActionEvent with flavor_key `{flavor_key}` already exists. Try adding a variant if you're sure it's not a duplicate.")
                    return

                new_id = action_events_crud.create_action_event(
                    session,
                    flavor_key=flavor_key,
                    action_id=action_id,
                    event_id=event_id,
                    points_granted=points_granted,
                    reward_event_id=reward_event_id,
                    self_reportable=self_reportable,
                    input_help_text=input_help_text,
                    created_by=str(interaction.user.id)
                )
                    
        except Exception as e:
            print(f"❌ DB failure: {e}")
            await interaction.followup.send("❌ An unexpected error occurred.")
            return
                
                await interaction.followup.send(f"✅ Linked Action `{action_id}` to Event `{event_id}`.")
                
            except IntegrityError:
                session.rollback()
                await interaction.followup.send("❌ This Action is already linked to this Event.")
                

    # === UPDATE ACTION EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="edit_action_event")
    @app_commands.describe(
        action_event_id="ID of the action-event link to edit",
        points_granted="Updated points (optional)",
        reward_event_id="Updated reward_event_id (optional)",
        self_reportable="Updated self-reportable flag",
        input_help_text="Updated help text (optional)"
    )
    async def edit_action_event(
        self,
        interaction: Interaction,
        action_event_id: int,
        points_granted: int = None,
        reward_event_id: int = None,
        self_reportable: bool = None,
        input_help_text: str = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        with db_session() as session:
            action_event = action_events_crud.get_action_event(session, action_event_id)
            if not action_event:
                await interaction.followup.send(f"❌ ActionEvent `{action_event_id}` not found.")
                return
            if events_crud.is_event_active(session, action_event.event_id):
                await interaction.followup.send("❌ Cannot edit actions for an active event.")
                return
            action_events_crud.update_action_event(
                session,
                action_event_id,
                points_granted=points_granted,
                reward_event_id=reward_event_id,
                self_reportable=self_reportable,
                input_help_text=input_help_text,
                modified_by=str(interaction.user.id),
                modified_at=str(datetime.utcnow())
            )
            await interaction.followup.send(f"✅ Updated ActionEvent `{action_event_id}`.")


    # === UNLINK ACTION EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="unlink_action_event")
    @app_commands.describe(action_event_id="ID of the action-event link to remove")
    async def unlink_action_event(self, interaction: Interaction, action_event_id: int):
        await interaction.response.defer(thinking=True, ephemeral=True)
        with db_session() as session:
            action_event = action_events_crud.get_action_event(session, action_event_id)
            if not action_event:
                await interaction.followup.send(f"❌ ActionEvent `{action_event_id}` not found.")
                return
            if events_crud.is_event_active(session, action_event.event_id):
                await interaction.followup.send("❌ Cannot unlink actions from an active event.")
                return
            action_events_crud.delete_action_event(session, action_event_id)
            await interaction.followup.send(f"✅ Unlinked ActionEvent `{action_event_id}`.")

    
    # ========== REWARD EVENT COMMANDS ==========
    # === LINK REWARD EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="link_reward_event")
    @app_commands.describe(
        reward_id="ID of the reward",
        event_id="ID of the event",
        availability="inshop or onaction",
        price="Price if availability is 'inshop'"
    )
    async def link_reward_event(
        self,
        interaction: Interaction,
        reward_id: int,
        event_id: int,
        availability: str = "inshop",
        price: int = 0
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        with db_session() as session:
            if events_crud.is_event_active(session, event_id):
                await interaction.followup.send("❌ Cannot link rewards to an active event.")
                return
            reward = crud.get_reward(session, reward_id)
            if not reward:
                await interaction.followup.send(f"❌ Reward `{reward_id}` not found.")
                return
            if reward.reward_type == "preset" and not reward.use_message_id:
                await interaction.followup.send("❌ Cannot attach a preset reward that has not been #published.")
                return
            try:
                new_id = action_events_crud.create_reward_event(
                    session,
                    reward_id=reward_id,
                    event_id=event_id,
                    availability=availability,
                    price=price
                )
                await interaction.followup.send(f"✅ Linked Reward `{reward_id}` to Event `{event_id}`.")
            except IntegrityError:
                session.rollback()
                await interaction.followup.send("❌ This Reward link already exists for this Event with this availability.")

    
    # === UPDATE REWARD EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="edit_reward_event")
    @app_commands.describe(
        reward_event_id="ID of the reward-event link to edit",
        availability="Updated availability (inshop/onaction)",
        price="Updated price"
    )
    async def edit_reward_event(
        self,
        interaction: Interaction,
        reward_event_id: int,
        availability: str = None,
        price: int = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        with db_session() as session:
            reward_event = reward_events_crud.get_reward_event(session, reward_event_id)
            if not reward_event:
                await interaction.followup.send(f"❌ RewardEvent `{reward_event_id}` not found.")
                return
            if events_crud.is_event_active(session, reward_event.event_id):
                await interaction.followup.send("❌ Cannot edit rewards for an active event.")
                return
            reward_events_crud.update_reward_event(
                session,
                reward_event_id,
                availability=availability,
                price=price
            )
            await interaction.followup.send(f"✅ Updated RewardEvent `{reward_event_id}`.")


    # === UNLINK REWARD EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="unlink_reward_event")
    @app_commands.describe(reward_event_id="ID of the reward-event link to remove")
    async def unlink_reward_event(self, interaction: Interaction, reward_event_id: int):
        await interaction.response.defer(thinking=True, ephemeral=True)
        with db_session() as session:
            reward_event = reward_events_crud.get_reward_event(session, reward_event_id)
            if not reward_event:
                await interaction.followup.send(f"❌ RewardEvent `{reward_event_id}` not found.")
                return
            if events_crud.is_event_active(session, reward_event.event_id):
                await interaction.followup.send("❌ Cannot unlink rewards from an active event.")
                return
            reward_events_crud.delete_reward_event(session, reward_event_id)
            await interaction.followup.send(f"✅ Unlinked RewardEvent `{reward_event_id}`.")


async def setup(bot):
    await bot.add_cog(EventLinksAdmin(bot))