import discord
from typing import Optional
from discord import app_commands, Interaction
from discord.ext import commands
from sqlalchemy.exc import IntegrityError
from bot.crud import action_events_crud, reward_events_crud, events_crud, rewards_crud, actions_crud
from bot.utils import admin_or_mod_check, paginate_embeds, now_iso, confirm_action
from db.database import db_session


class EventLinksAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin_links = app_commands.Group(
        name="admin_links",
        description="Manage Action-Event and Reward-Event links (Admin only)."
    )

    
    # ========== REWARD EVENT COMMANDS ==========
    # === LINK REWARD EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="link_reward_event")
    @app_commands.choices(
        availability=[
            app_commands.Choice(name="in shop", value="inshop"),
            app_commands.Choice(name="on action", value="onaction")
        ]
    )
    @app_commands.describe(
        event_shortcode="Shortcode of the event",
        reward_shortcode="Shortcode of the reward",
        availability="in shop or on action",
        price="Price if availability is 'in shop'"
    )
    async def link_reward_event(
        self,
        interaction: Interaction,
        event_shortcode: str,
        reward_shortcode: str,
        availability: app_commands.Choice[str],
        price: int = 0
    ):
        """Link a reward to an event."""
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            with db_session() as session:
                event = events_crud.get_event_by_key(session, event_shortcode)
                if not event:
                    await interaction.followup.send(f"❌ Event `{event_shortcode}` not found.")
                    return
                if events_crud.is_event_active(session, event.id):
                    await interaction.followup.send("❌ Cannot link rewards to an active event.")
                    return

                reward = rewards_crud.get_reward_by_key(session, reward_shortcode)
                if not reward:
                    await interaction.followup.send(f"❌ Reward `{reward_shortcode}` not found.")
                    return
                if reward.reward_type == "preset" and not reward.use_message_discord_id:
                    await interaction.followup.send("❌ Cannot attach to an unpublished preset reward.")
                    return

                # Auto-generate key
                reward_event_key = f"{event_shortcode.lower()}_{reward_shortcode.lower()}_{availability.value}"

                existing_re = reward_events_crud.get_reward_event_by_key(session, reward_event_key)
                if existing_re:
                    await interaction.followup.send(
                        f"❌ The reward **{reward.reward_name}** (`{reward.reward_key}`) "
                        f"is already linked to the event **{event.event_name}** (`{event.event_key}`) "
                        f"with the availability '{availability.name}'."
                    )
                    return

                if price < 0:
                    await interaction.followup.send("❌ Price must be a non-negative number.")
                    return
                if availability.value == "onaction" and price != 0:
                    await interaction.followup.send("❌ Price must be 0 when availability is 'on action'.")
                    return

                re_create_data = {
                    "reward_event_key": reward_event_key,
                    "reward_id": reward.id,
                    "event_id": event.id,
                    "availability": availability.value,
                    "price": price,
                    "created_by": str(interaction.user.id)
                }

                reward_event = reward_events_crud.create_reward_event(session, re_create_data)

                await interaction.followup.send(
                    f"✅ Linked reward **{reward.reward_name}** (`{reward.reward_key}`) "
                    f"to event **{event.event_name}** (`{event.event_key}`) "
                    f"with the shortcode `{reward_event.reward_event_key}`."
                )

        except Exception as e:
            print(f"❌ DB failure: {e}")
            await interaction.followup.send("❌ An unexpected error occurred.")


    # === EDIT REWARD EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="edit_reward_event")
    @app_commands.choices(
        availability=[
            app_commands.Choice(name="in shop", value="inshop"),
            app_commands.Choice(name="on action", value="onaction")
        ]
    )
    @app_commands.describe(
        reward_event_key="Shortcode of the reward-event link to edit",
        availability="Updated availability (in shop/on action)",
        price="Updated price",
        reason="Optional reason for editing (will be logged)",
        force="Override restrictions for active events"
    )
    async def edit_reward_event(
        self,
        interaction: Interaction,
        reward_event_key: str,
        availability: Optional[app_commands.Choice[str]] = None,
        price: Optional[int] = None,
        reason: Optional[str] = None,
        force: bool = False
    ):
        """Edit the availability and/or price of a reward-event link."""
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward_event = reward_events_crud.get_reward_event_by_key(session, reward_event_key)
            if not reward_event:
                await interaction.followup.send(f"❌ Reward-event link `{reward_event_key}` not found.")
                return
                
            if events_crud.is_event_active(session, reward_event.event_id):
                if not force:
                    await interaction.followup.send(
                        "❌ Cannot edit a reward-event linked to an active event without `--force`."
                    )
                    return
                else:
                    confirmed = await confirm_action(
                        interaction=interaction,
                        item_name=f"the reward-event `{reward_event_key}` linked to an ACTIVE event",
                        item_action="force_edit",
                        reason="⚠️ **FORCED EDIT** — this may affect participants!"
                    )
                    if not confirmed:
                        await interaction.followup.send("❌ Forced edit cancelled or timed out.")
                        return

            # Use new availability if provided, else keep current
            availability_value = availability.value if availability else reward_event.availability

            re_update_data = {}
            if availability and availability_value != reward_event.availability:
                re_update_data["availability"] = availability_value

            if price is not None and price != reward_event.price:
                if price < 0:
                    await interaction.followup.send("❌ Price must be a non-negative number.")
                    return
                if availability_value == "onaction" and price != 0:
                    await interaction.followup.send("❌ Price must be 0 when availability is 'on action'.")
                    return
                re_update_data["price"] = price

            if not re_update_data:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return

            re_update_data["modified_by"] = str(interaction.user.id)

            reward_events_crud.update_reward_event(
                session, reward_event_key, re_update_data, reason, force
            )

            await interaction.followup.send(
                f"✅ Updated reward-event **{reward_event.reward.reward_name}** "
                f"(`{reward_event.reward.reward_key}`) for event **{reward_event.event.event_name}** "
                f"(`{reward_event.event.event_key}`)."
            )


    # === UNLINK REWARD EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="unlink_reward_event")
    @app_commands.describe(
        reward_event_key="Shortcode of the reward-event link to remove",
        reason="Reason for deleting (will be logged)",
        force="Override restrictions for active events"
    )
    async def unlink_reward_event(
        self,
        interaction: Interaction,
        reward_event_key: str,
        reason: str,
        force: bool = False
    ):
        """Unlink a reward from an event."""
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward_event = reward_events_crud.get_reward_event_by_key(session, reward_event_key)
            if not reward_event:
                await interaction.followup.send(f"❌ Reward-event link `{reward_event_key}` not found.")
                return

            # Active event restriction
            if events_crud.is_event_active(session, reward_event.event_id):
                if not force:
                    await interaction.followup.send(
                        "❌ Cannot unlink a reward-event from an active event without `--force`."
                    )
                    return
                else:
                    confirmed = await confirm_action(
                        interaction=interaction,
                        item_name=f"the reward-event `{reward_event_key}` linked to an ACTIVE event",
                        item_action="force_delete",
                        reason="⚠️ **FORCED UNLINK** — this will impact participants!"
                    )
                    if not confirmed:
                        await interaction.followup.send("❌ Forced unlink cancelled or timed out.")
                        return

            reward_events_crud.delete_reward_event(
                session, reward_event_key, str(interaction.user.id), reason, force
            )

            await interaction.followup.send(
                f"✅ Unlinked reward **{reward_event.reward.reward_name}** "
                f"(`{reward_event.reward.reward_key}`) from event **{reward_event.event.event_name}** "
                f"(`{reward_event.event.event_key}`)."
            )


    # ========== ACTION EVENT COMMANDS ==========
    
    # === LINK ACTION EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="link_action_event")
    @app_commands.describe(
        action_shortcode="Shortcode of the action to link",
        event_shortcode="Shortcode of the event to link to",
        input_help_text="Guidance text for input",
        variant="Optional short label to distinguish this variant (e.g., 'current', 'past')",
        points_granted="Optional points to grant for this action in this event",
        reward_event_key="Optional shortcode of linked reward_event",
        allowed_during_visible="Allow action during event 'visible' status",
        self_reportable="Can the user report this action themselves?"
    )
    async def link_action_event(
        self,
        interaction: Interaction,
        action_shortcode: str,
        event_shortcode: str,
        input_help_text: str,
        variant: str = "default",
        points_granted: int = 0,
        reward_event_key: Optional[str] = None,
        allowed_during_visible: bool = False,
        self_reportable: bool = True
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        try:
            with db_session() as session:
                # --- Validate Event ---
                event = events_crud.get_event_by_key(session, event_shortcode)
                if not event:
                    await interaction.followup.send(f"❌ Event `{event_shortcode}` not found.")
                    return
                if events_crud.is_event_active(session, event.id):
                    await interaction.followup.send("❌ Cannot link actions to an active event.")
                    return
    
                # --- Validate Action ---
                action = actions_crud.get_action_by_key(session, action_shortcode)
                if not action:
                    await interaction.followup.send(f"❌ Action `{action_shortcode}` not found.")
                    return
    
                # --- Validate Reward-Event if provided ---
                if reward_event_key:
                    reward_event = reward_events_crud.get_reward_event_by_key(session, reward_event_key)
                    if not reward_event:
                        await interaction.followup.send(f"❌ Reward-event `{reward_event_key}` not found.")
                        return
    
                # --- Validate points ---
                if points_granted < 0:
                    await interaction.followup.send("❌ Points granted must be 0 or a positive number.")
                    return
    
                # --- Build unique action_event_key ---
                variant_clean = variant.strip().lower().replace(" ", "_")
                action_event_key = f"{event_shortcode.lower()}_{action_shortcode.lower()}_{variant_clean}"
    
                # --- Check for duplicate link ---
                existing_ae = action_events_crud.get_action_event_by_key(session, action_event_key)
                if existing_ae:
                    await interaction.followup.send(
                        f"❌ The action **{action.action_key}** is already linked to the event "
                        f"**{event.event_name}** (`{event.event_key}`) with variant '{variant_clean}'."
                    )
                    return
    
                # --- Create dict for CRUD ---
                ae_create_data = {
                    "action_event_key": action_event_key,
                    "action_id": action.id,
                    "event_id": event.id,
                    "variant": variant_clean,
                    "points_granted": points_granted,
                    "reward_event_id": reward_event.id if reward_event_key else None,
                    "is_allowed_during_visible": allowed_during_visible,
                    "is_self_reportable": self_reportable,
                    "input_help_text": input_help_text,
                    "created_by": str(interaction.user.id)
                }
    
                action_event = action_events_crud.create_action_event(session, ae_create_data)
    
                await interaction.followup.send(
                    f"✅ Linked action **{action.action_key}** (`{action.action_key}`) "
                    f"to event **{event.event_name}** (`{event.event_key}`) "
                    f"with the shortcode `{action_event.action_event_key}`."
                )
    
        except Exception as e:
            print(f"❌ DB failure: {e}")
            await interaction.followup.send("❌ An unexpected error occurred.")
    
    
    # === EDIT ACTION EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="edit_action_event")
    @app_commands.describe(
        action_event_key="Shortcode of the action-event link to edit",
        points_granted="Updated points (optional)",
        reward_event_key="Updated reward-event link (optional)",
        allowed_during_visible="Updated allowed-during-visible flag",
        self_reportable="Updated self-reportable flag",
        input_help_text="Updated help text (optional)",
        reason="Reason for editing (will be logged)"
    )
    async def edit_action_event(
        self,
        interaction: Interaction,
        action_event_key: str,
        points_granted: Optional[int] = None,
        reward_event_key: Optional[str] = None,
        allowed_during_visible: Optional[bool] = None,
        self_reportable: Optional[bool] = None,
        input_help_text: Optional[str] = None,
        reason: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            action_event = action_events_crud.get_action_event_by_key(session, action_event_key)
            if not action_event:
                await interaction.followup.send(f"❌ Action-event `{action_event_key}` not found.")
                return
            if events_crud.is_event_active(session, action_event.event_id):
                await interaction.followup.send("❌ Cannot edit actions for an active event.")
                return
    
            re_update_data = {}
    
            if points_granted is not None and points_granted != action_event.points_granted:
                if points_granted < 0:
                    await interaction.followup.send("❌ Points must be 0 or positive.")
                    return
                re_update_data["points_granted"] = points_granted
    
            if reward_event_key is not None:
                reward_event = reward_events_crud.get_reward_event_by_key(session, reward_event_key)
                if not reward_event:
                    await interaction.followup.send(f"❌ Reward-event `{reward_event_key}` not found.")
                    return
                re_update_data["reward_event_id"] = reward_event.id
    
            if allowed_during_visible is not None:
                re_update_data["is_allowed_during_visible"] = allowed_during_visible
    
            if self_reportable is not None:
                re_update_data["is_self_reportable"] = self_reportable
    
            if input_help_text is not None and input_help_text != action_event.input_help_text:
                re_update_data["input_help_text"] = input_help_text
    
            if not re_update_data:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return
    
            re_update_data["modified_by"] = str(interaction.user.id)
    
            action_events_crud.update_action_event(
                session, action_event_key, re_update_data, reason
            )
    
            await interaction.followup.send(
                f"✅ Updated action-event **{action_event.action.action_key}** "
                f"(`{action_event.action_event_key}`) for event **{action_event.event.event_name}** "
                f"(`{action_event.event.event_key}`)."
            )
    
    
    # === UNLINK ACTION EVENT ===
    @admin_or_mod_check()
    @admin_links.command(name="unlink_action_event")
    @app_commands.describe(
        action_event_key="Shortcode of the action-event link to remove",
        reason="Reason for deleting (will be logged)"
    )
    async def unlink_action_event(
        self,
        interaction: Interaction,
        action_event_key: str,
        reason: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            action_event = action_events_crud.get_action_event_by_key(session, action_event_key)
            if not action_event:
                await interaction.followup.send(f"❌ Action-event `{action_event_key}` not found.")
                return
            if events_crud.is_event_active(session, action_event.event_id):
                await interaction.followup.send("❌ Cannot unlink actions from an active event.")
                return
    
            action_events_crud.delete_action_event(
                session, action_event_key, str(interaction.user.id), reason
            )
    
            await interaction.followup.send(
                f"✅ Unlinked action **{action_event.action.action_key}** "
                f"(`{action_event.action_event_key}`) from event **{action_event.event.event_name}** "
                f"(`{action_event.event.event_key}`)."
            )
    
        



async def setup(bot):
    await bot.add_cog(EventLinksAdmin(bot))