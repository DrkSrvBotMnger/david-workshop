from discord import app_commands, Interaction
from discord.ext import commands
from bot.utils.time_parse_paginate import admin_or_mod_check, now_iso
from db.database import db_session
from db.schema import RewardEvent, ActionEvent, Action
from bot.crud import events_crud, rewards_crud, reward_events_crud, actions_crud, action_events_crud
from bot.utils.time_parse_paginate import parse_required_fields, parse_help_texts
from bot.config.constants import CURRENCY
from bot.ui.admin.event_link_views import (
    EventSelect, RewardSelect, RewardEventSelect, AvailabilitySelect, PricePicker, ForceConfirmView, ActionEventSelect,
    ActionSelect, VariantPickerView, HelpTextPerFieldView, YesNoView, ToggleYesNoView,
    SingleSelectView, PointPickerView
)

class EventLinksAdminFriendly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin_links = app_commands.Group(
        name="admin_links",
        description="Manage Reward-Event links with optional action linking"
    )

    @admin_or_mod_check()
    @admin_links.command(name="link_reward_event")
    async def link_reward_event(self, interaction: Interaction):
        """Link a reward to an event, optionally attaching an action if on-action."""
        await interaction.response.defer(ephemeral=True)
        force = False

        msg_timeout=("❌ Action timed out and cancelled.")
        
        with db_session() as session:
            # === Step 1: Select Event ===
            events = events_crud.get_all_events(session)
            if not events:
                return await interaction.followup.send("❌ No events found.", ephemeral=True)

            event_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select the event:", view=event_view, ephemeral=True)
            await event_view.wait()
            if not event_view.selected_event_key:
                return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)

            event = events_crud.get_event_by_key(session, event_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)

            # Active event check
            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Link anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)
                force = True

            # === Step 2: Select Reward (only unlinked) ===
            all_rewards = rewards_crud.get_all_rewards(session)
            linked_ids = {re.reward_id for re in session.query(RewardEvent).filter_by(event_id=event.id).all()}
            available_rewards = [rw for rw in all_rewards if rw.id not in linked_ids]

            if not available_rewards:
                return await interaction.followup.send(
                    f"❌ All rewards are already linked to **{event.event_name}**.",
                    ephemeral=True
                )

            reward_view = SingleSelectView(RewardSelect(available_rewards))
            await interaction.followup.send("📌 Select the reward:", view=reward_view, ephemeral=True)
            await reward_view.wait()
            if not reward_view.selected_reward_key:
                return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)

            reward = rewards_crud.get_reward_by_key(session, reward_view.selected_reward_key)
            if not reward:
                return await interaction.followup.send("❌ Invalid reward.", ephemeral=True)

            # === Step 3: Select Availability ===
            avail_view = SingleSelectView(AvailabilitySelect())
            await interaction.followup.send("📌 Select availability:", view=avail_view, ephemeral=True)
            await avail_view.wait()
            if not avail_view.selected_availability:
                return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)
            availability = avail_view.selected_availability

            # === Step 4: Price ===
            price = 0
            if availability == "inshop":
                picker = PricePicker()
                await interaction.followup.send("💰 Choose a price:", view=picker, ephemeral=True)
                await picker.wait()
                if picker.selected_price is None:
                    return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)
                price = picker.selected_price

            # === Step 5: Create Reward-Event ===
            re_key = f"{event.event_key.lower()}_{reward.reward_key.lower()}_{availability}"
            if reward_events_crud.get_reward_event_by_key(session, re_key):
                return await interaction.followup.send("❌ This reward is already linked.", ephemeral=True)

            iso_now = now_iso()
            
            reward_event = reward_events_crud.create_reward_event(
                session,
                {
                    "reward_event_key": re_key,
                    "reward_id": reward.id,
                    "event_id": event.id,
                    "availability": availability,
                    "price": price,
                    "created_by": str(interaction.user.id),
                    "created_at": iso_now
                },
                force=force
            )
            
            # === Step 6: Announce reward creation ===
            if availability == "inshop":
                availability_display = f"in shop for {price} {CURRENCY}"
            else:
                availability_display = "on action"

            msg_re_success=(f"✅ Linked reward **{reward.reward_name}** to event **{event.event_name}** — {availability_display}")
            msg_ae_fail=("❌ No action was linked.")
            
            if availability == "inshop":
                return await interaction.followup.send(f"{msg_re_success}", ephemeral=True)

            # === Step 7: Optional action attachment ===
            if availability == "onaction":
                attach_view = YesNoView("Do you want to attach an action to this reward now?")
                await interaction.followup.send(attach_view.prompt, view=attach_view, ephemeral=True)
                await attach_view.wait()
                if attach_view.confirmed is None:
                    return await interaction.followup.send(
                        f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                        ephemeral=True
                    )
                if attach_view.confirmed is False:
                    return await interaction.followup.send(
                        f"{msg_re_success}\n{msg_ae_fail}",
                        ephemeral=True
                    )

                if attach_view.confirmed:
                    # === Step A: Get all active actions ===
                    active_actions = [a for a in actions_crud.get_all_actions(session) if a.is_active]
                    if not active_actions:
                        await interaction.followup.send(
                            f"❌ No active actions available for **{event.event_name}**.\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                        return

                    # === Step B: Select Action ===
                    action_view = SingleSelectView(ActionSelect(active_actions))
                    await interaction.followup.send("📌 Select the action:", view=action_view, ephemeral=True)
                    await action_view.wait()
                    if not action_view.selected_action_key:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    action = actions_crud.get_action_by_key(session, action_view.selected_action_key)
                    if not action:
                        await interaction.followup.send(
                            f"❌ Invalid action.\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                        return

                    # === Step C: Select Variant ===
                    variant_picker = VariantPickerView()
                    await interaction.followup.send("📌 Select variant:", view=variant_picker, ephemeral=True)
                    await variant_picker.wait()
                    if not variant_picker.selected_variant:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )             

                    variant = variant_picker.selected_variant

                    # --- Build unique action_event_key ---
                    variant_clean = variant.strip().lower().replace(" ", "_")
                    ae_key = f"{event.event_key.lower()}_{action.action_key.lower()}_{variant_clean}"
                    
                    # Duplicate check for action-event variant
                    if action_events_crud.get_action_event_by_key(session, ae_key):
                        await interaction.followup.send(
                            f"❌ Action '{action.action_key}' with variant '{variant}' already exists for the event.\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                        return

                    # === Step D: is_allowed_during_visible ===
                    allowed_view = ToggleYesNoView("Allow during visible period?")
                    await interaction.followup.send(allowed_view.prompt, view=allowed_view, ephemeral=True)
                    await allowed_view.wait()
                    if allowed_view.value is None:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    is_allowed_during_visible = allowed_view.value

                    # === Step E: is_self_reportable ===
                    reportable_view = ToggleYesNoView("Allow self-report?")
                    await interaction.followup.send(reportable_view.prompt, view=reportable_view, ephemeral=True)
                    await reportable_view.wait()
                    if reportable_view.value is None:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    is_self_reportable = reportable_view.value

                    # === Step F: is_repeatable ===
                    repeatable_view = ToggleYesNoView("Allow action to be repeated?")
                    await interaction.followup.send(repeatable_view.prompt, view=repeatable_view, ephemeral=True)
                    await repeatable_view.wait()
                    if repeatable_view.value is None:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    is_repeatable = repeatable_view.value
                    
                    # === Step G: Input help text ===
                    action_fields = parse_required_fields(action.input_fields_json)    
                    help_view = HelpTextPerFieldView(fields=action_fields)
                    await interaction.followup.send("💬 Add help text? (General + one per selected field)", view=help_view, ephemeral=True)
                    await help_view.wait()
                    if help_view.help_texts_json is None:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    if help_view.help_texts_json is False:
                        input_help_json = ""  # user chose No
                    else:
                        input_help_json = help_view.help_texts_json  # already JSON string
    
                    # === Step H: Create Action-Event ===
                    action_events_crud.create_action_event(
                        session,
                        {
                            "action_event_key": ae_key,
                            "action_id": action.id,
                            "event_id": event.id,
                            "variant": variant,
                            "is_allowed_during_visible": is_allowed_during_visible,
                            "is_self_reportable": is_self_reportable,
                            "is_repeatable": is_repeatable,
                            "input_help_json": input_help_json,
                            "reward_event_id": reward_event.id,
                            "created_by": str(interaction.user.id),
                            "created_at": iso_now
                        },
                        force=force
                    )

                    action_key = action.action_key
                    
                    await interaction.followup.send(
                        f"{msg_re_success}\n"
                        f"✅ Linked action **{action_key}** ({variant}) to the reward.",
                        ephemeral=True
                    )

    
    # ====== EDIT REWARD EVENT ======
    @admin_or_mod_check()
    @admin_links.command(name="edit_reward_event")
    async def edit_reward_event(self, interaction: Interaction):
        """Edit a reward-event link, including price or attached action-event."""
        await interaction.response.defer(ephemeral=True)
        force = False

        msg_timeout=("❌ Action timed out and cancelled.")
        
        with db_session() as session:
            # === Step 1: Select Event ===
            events = events_crud.get_all_events(session)
            event_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select event:", view=event_view, ephemeral=True)
            await event_view.wait()
            if not event_view.selected_event_key:
                return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)

            event = events_crud.get_event_by_key(session, event_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)

            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Edit anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send("❌ Edit cancelled.", ephemeral=True)
                force = True

            # === Step 2: Select Reward-Event to Edit ===
            reward_events = reward_events_crud.get_all_reward_events_for_event(session, event.id)
            if not reward_events:
                return await interaction.followup.send(
                    f"❌ No rewards are linked to **{event.event_name}**.", ephemeral=True
                )
            re_view = SingleSelectView(RewardEventSelect(reward_events))
            await interaction.followup.send("📌 Select reward-event to edit:", view=re_view, ephemeral=True)
            await re_view.wait()
            if not re_view.selected_reward_event_key:
                return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)

            reward_event = reward_events_crud.get_reward_event_by_key(session, re_view.selected_reward_event_key)
            if not reward_event:
                return await interaction.followup.send("❌ Invalid reward-event.", ephemeral=True)

            original_availability = reward_event.availability
            existing_action_event = session.query(action_events_crud.ActionEvent).filter_by(
                reward_event_id=reward_event.id).first()

            # === Step 3: Choose New Availability ===
            avail_view = SingleSelectView(AvailabilitySelect())
            await interaction.followup.send("📌 Select new availability:", view=avail_view, ephemeral=True)
            await avail_view.wait()
            if not avail_view.selected_availability:
                return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)

            new_availability = avail_view.selected_availability

            # === Step 4: Choose Price if inshop ===
            new_price = 0
            if new_availability == "inshop":
                picker = PricePicker()
                await interaction.followup.send("💰 Choose new price:", view=picker, ephemeral=True)
                await picker.wait()
                if picker.selected_price is None:
                    return await interaction.followup.send(f"{msg_timeout}", ephemeral=True)
                new_price = picker.selected_price

            iso_now = now_iso()
            
            # === Step 5: Update reward-event itself ===
            reward_events_crud.update_reward_event(
                session,
                reward_event.reward_event_key,
                {
                    "availability": new_availability,
                    "price": new_price,
                    "modified_by": str(interaction.user.id),
                    "modified_at": iso_now
                },
                force=force
            )

            # === Step 6: Remove existing AE ===
            if existing_action_event:
                action_events_crud.delete_action_event(
                    session,
                    existing_action_event.action_event_key, 
                    str(interaction.user.id),
                    iso_now,
                    force=force)
                session.flush()

            if new_availability == "inshop":
                new_availability_display = f"now in shop for {new_price} {CURRENCY}"
            else:
                new_availability_display = "now on action"

            msg_re_success=(f"✅ Updated reward **{reward_event.reward.reward_name}** to event **{event.event_name}** — {new_availability_display}")
            msg_ae_fail=("No new action was linked.")
            msg_del_success=("")
            
            if original_availability == "onaction":
                msg_del_success = ("🗑️ Removed any previous action-event link. ")
                
            if new_availability == "inshop":
                    return await interaction.followup.send(f"{msg_re_success}\n{msg_del_success}", ephemeral=True)
            
            # === Step 7: Action attachment ===
            if new_availability == "onaction":
                attach_view = YesNoView("Do you want to attach an action to this reward now?")
                await interaction.followup.send(attach_view.prompt, view=attach_view, ephemeral=True)
                await attach_view.wait()
                if attach_view.confirmed is None:
                    return await interaction.followup.send(f"{msg_timeout}\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                        ephemeral=True
                    )
                if attach_view.confirmed is False:
                    return await interaction.followup.send(f"{msg_ae_fail}\n{msg_re_success}",
                        ephemeral=True
                    )
        
                if attach_view.confirmed:
                    # === Step A: Get all active actions ===
                    active_actions = [a for a in actions_crud.get_all_actions(session) if a.is_active]
                    if not active_actions:
                        await interaction.followup.send(
                            f"❌ No active actions available for **{event.event_name}**.\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                        ephemeral=True
                    )
                        return
        
                    # === Step B: Select Action ===
                    action_view = SingleSelectView(ActionSelect(active_actions))
                    await interaction.followup.send("📌 Select the action:", view=action_view, ephemeral=True)
                    await action_view.wait()
                    if not action_view.selected_action_key:
                        return await interaction.followup.send(f"{msg_timeout}\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    action = actions_crud.get_action_by_key(session, action_view.selected_action_key)
                    if not action:
                        return await interaction.followup.send(f"❌ Invalid action.\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                        return
        
                    # === Step C: Select Variant ===
                    variant_picker = VariantPickerView()
                    await interaction.followup.send("📌 Select variant:", view=variant_picker, ephemeral=True)
                    await variant_picker.wait()
                    if not variant_picker.selected_variant:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    variant = variant_picker.selected_variant
        
                    # --- Build unique action_event_key ---
                    variant_clean = variant.strip().lower().replace(" ", "_")
                    ae_key = f"{event.event_key.lower()}_{action.action_key.lower()}_{variant_clean}"
        
                    # Duplicate check for action-event variant
                    if action_events_crud.get_action_event_by_key(session, ae_key):
                        await interaction.followup.send(
                            f"❌ Action '{action.action_key}' with variant '{variant}' already exists for the event.\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                        return
        
                    # === Step D: is_allowed_during_visible ===
                    allowed_view = ToggleYesNoView("Allow during visible period?")
                    await interaction.followup.send(allowed_view.prompt, view=allowed_view, ephemeral=True)
                    await allowed_view.wait()
                    if allowed_view.value is None:
                        return await interaction.followup.send(f"{msg_timeout}\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    is_allowed_during_visible = allowed_view.value
        
                    # === Step E: is_self_reportable ===
                    reportable_view = ToggleYesNoView("Allow self-report?")
                    await interaction.followup.send(reportable_view.prompt, view=reportable_view, ephemeral=True)
                    await reportable_view.wait()
                    if reportable_view.value is None:
                        return await interaction.followup.send(f"{msg_timeout}\n{msg_del_success}{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    is_self_reportable = reportable_view.value

                    # === Step F: is_repeatable ===
                    repeatable_view = ToggleYesNoView("Allow action to be repeated?")
                    await interaction.followup.send(repeatable_view.prompt, view=repeatable_view, ephemeral=True)
                    await repeatable_view.wait()
                    if repeatable_view.value is None:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    is_repeatable = repeatable_view.value
        
                    # === Step G: Input help text ===
                    action_fields = parse_required_fields(action.input_fields_json)  
                    help_view = HelpTextPerFieldView(fields=action_fields)
                    await interaction.followup.send("💬 Add help text? (General + one per selected field)", view=help_view, ephemeral=True)
                    await help_view.wait()
                    if help_view.help_texts_json is None:
                        return await interaction.followup.send(
                            f"{msg_timeout}\n{msg_ae_fail}\n{msg_re_success}",
                            ephemeral=True
                        )
                    if help_view.help_texts_json is False:
                        input_help_json = ""  # user chose No
                    else:
                        input_help_json = help_view.help_texts_json  # already JSON string
        
                    # === Step H: Create Action-Event ===
                    action_events_crud.create_action_event(
                        session,
                        {
                            "action_event_key": ae_key,
                            "action_id": action.id,
                            "event_id": event.id,
                            "variant": variant,
                            "is_allowed_during_visible": is_allowed_during_visible,
                            "is_self_reportable": is_self_reportable,
                            "is_repeatable": is_repeatable,
                            "input_help_json": input_help_json,
                            "reward_event_id": reward_event.id,
                            "created_by": str(interaction.user.id),
                            "created_at": iso_now
                        },
                        force=force
                    )
        
                    action_key = action.action_key
        
                    await interaction.followup.send(
                        f"{msg_re_success}\n"
                        f"✅ Linked action **{action_key}** ({variant}) to the reward.",
                        ephemeral=True
                    )


    # ====== UNLINK REWARD EVENT ======
    @admin_or_mod_check()
    @admin_links.command(name="unlink_reward_event")
    async def unlink_reward_event(self, interaction: Interaction):
        """Unlink a reward from an event."""
        await interaction.response.defer(ephemeral=True)
        force = False
    
        with db_session() as session:
            # Step 1: Select event
            events = events_crud.get_all_events(session)
            if not events:
                return await interaction.followup.send("❌ No events found.", ephemeral=True)
    
            event_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select event:", view=event_view, ephemeral=True)
            await event_view.wait()
    
            event = events_crud.get_event_by_key(session, event_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)
    
            # Step 2: Active event check
            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Unlink anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send("❌ Unlink cancelled.", ephemeral=True)
                force = True
    
            # Step 3: Get linked reward-events
            reward_events = reward_events_crud.get_all_reward_events_for_event(session, event.id)
    
            # Early exit if none linked
            if not reward_events:
                return await interaction.followup.send(
                    f"❌ No rewards are linked to **{event.event_name}**.",
                    ephemeral=True
                )
    
            # Step 4: Select reward-event to unlink
            re_view = SingleSelectView(RewardEventSelect(reward_events))
            await interaction.followup.send("📌 Select reward-event to unlink:", view=re_view, ephemeral=True)
            await re_view.wait()
    
            reward_event = reward_events_crud.get_reward_event_by_key(session, re_view.selected_reward_event_key)
            if not reward_event:
                return await interaction.followup.send("❌ Invalid reward-event.", ephemeral=True)
    
            # Step 5: Delete any associated action-event
            linked_action_event = session.query(action_events_crud.ActionEvent).filter_by(
                reward_event_id=reward_event.id
            ).first()

            iso_now = now_iso()

            msg_ae_deleted = ""
            if linked_action_event:
                action_events_crud.delete_action_event(
                    session,
                    linked_action_event.action_event_key, 
                    str(interaction.user.id),
                    iso_now,
                    force=force)
                session.flush()
                msg_ae_deleted = f"🗑️ Deleted associated action-event: `{linked_action_event.action_event_key}`"

            # Step 6: Unlink reward-event
            reward_events_crud.delete_reward_event(
                session,
                reward_event.reward_event_key,
                str(interaction.user.id),
                iso_now,
                force=force
            )
            await interaction.followup.send(
                f"✅ Unlinked **{reward_event.reward.reward_name}** from **{event.event_name}**.\n{msg_ae_deleted}",
                ephemeral=True
            )


    # ====== CREATE ACTION EVENT ======
    @admin_or_mod_check()
    @admin_links.command(name="create_action_event")
    async def create_action_event(self, interaction: Interaction):
        """Create a standalone action-event (not linked to a reward)."""
        await interaction.response.defer(ephemeral=True)
        force = False
        msg_timeout = "❌ Action timed out and cancelled."
    
        with db_session() as session:
            # === Step 1: Select Event ===
            events = events_crud.get_all_events(session)
            event_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select the event:", view=event_view, ephemeral=True)
            await event_view.wait()
            if not event_view.selected_event_key:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            event = events_crud.get_event_by_key(session, event_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)
    
            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Create anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send("❌ Cancelled.", ephemeral=True)
                force = True
    
            # === Step 2: Select Action ===
            active_actions = [a for a in actions_crud.get_all_actions(session) if a.is_active]
            if not active_actions:
                return await interaction.followup.send("❌ No active actions found.", ephemeral=True)
    
            action_view = SingleSelectView(ActionSelect(active_actions))
            await interaction.followup.send("📌 Select the action:", view=action_view, ephemeral=True)
            await action_view.wait()
            if not action_view.selected_action_key:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            action = actions_crud.get_action_by_key(session, action_view.selected_action_key)
            if not action:
                return await interaction.followup.send("❌ Invalid action.", ephemeral=True)
    
            # === Step 3: Input Variant ===
            variant_picker = VariantPickerView()
            await interaction.followup.send("📌 Enter variant:", view=variant_picker, ephemeral=True)
            await variant_picker.wait()
            if not variant_picker.selected_variant:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            variant = variant_picker.selected_variant
            variant_clean = variant.strip().lower().replace(" ", "_")
            ae_key = f"{event.event_key.lower()}_{action.action_key.lower()}_{variant_clean}"
    
            if action_events_crud.get_action_event_by_key(session, ae_key):
                return await interaction.followup.send(
                    f"❌ Action-event `{ae_key}` already exists for this event.",
                    ephemeral=True
                )
    
            # === Step 4: Select Points Granted ===
            point_picker = PointPickerView()
            await interaction.followup.send(
                "**How many points should this action grant?**\n"
                "_To link a reward to this action instead, use the command `link_reward_event`._",
                view=point_picker,
                ephemeral=True
            )
            await point_picker.wait()
            if point_picker.cancelled:
                return await interaction.followup.send("❌ Cancelled by user.", ephemeral=True)
            if point_picker.custom_points is not None:
                points_granted = point_picker.custom_points
            elif point_picker.selected_points is not None:
                points_granted = point_picker.selected_points
            else:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            # === Step 5: is_allowed_during_visible ===
            allowed_view = ToggleYesNoView("Allow during visible period?")
            await interaction.followup.send(allowed_view.prompt, view=allowed_view, ephemeral=True)
            await allowed_view.wait()
            if allowed_view.value is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            is_allowed_during_visible = allowed_view.value
    
            # === Step 6: is_self_reportable ===
            reportable_view = ToggleYesNoView("Allow self-reporting?")
            await interaction.followup.send(reportable_view.prompt, view=reportable_view, ephemeral=True)
            await reportable_view.wait()
            if reportable_view.value is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            is_self_reportable = reportable_view.value

            # === Step 7: is_repeatable ===
            repeatable_view = ToggleYesNoView("Allow action to be repeated?")
            await interaction.followup.send(repeatable_view.prompt, view=repeatable_view, ephemeral=True)
            await repeatable_view.wait()
            if repeatable_view.value is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            is_repeatable = repeatable_view.value
    
            # === Step 8: Help Text? ===

            action_fields = parse_required_fields(action.input_fields_json)
            help_view = HelpTextPerFieldView(fields=action_fields)
            await interaction.followup.send("💬 Add help text? (General + one per selected field)", view=help_view, ephemeral=True)
            await help_view.wait()
            if help_view.help_texts_json is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            if help_view.help_texts_json is False:
                input_help_json = ""  # user chose No
            else:
                input_help_json = help_view.help_texts_json  # already JSON string
    
            # === Step 9: Create Action-Event ===
            iso_now = now_iso()
            ae = action_events_crud.create_action_event(
                session,
                {
                    "action_event_key": ae_key,
                    "action_id": action.id,
                    "event_id": event.id,
                    "variant": variant,
                    "points_granted": points_granted,
                    "is_allowed_during_visible": is_allowed_during_visible,
                    "is_self_reportable": is_self_reportable,
                    "is_repeatable": is_repeatable,
                    "input_help_json": input_help_json,
                    "reward_event_id": None,
                    "created_by": str(interaction.user.id),
                    "created_at": iso_now
                },
                force=force
            )
    
            return await interaction.followup.send(
                f"✅ Created action-event **{action.action_key}** ({variant}) for event **{event.event_name}** "
                f"granting **{points_granted}** points.",
                ephemeral=True
            )

    
    # ====== EDIT ACTION EVENT ======
    @admin_or_mod_check()
    @admin_links.command(name="edit_action_event")
    async def edit_action_event(self, interaction: Interaction):
        """Edit a standalone action-event (not linked to a reward)."""
        await interaction.response.defer(ephemeral=True)
        force = False
        msg_timeout = "❌ Action timed out and cancelled."
    
        with db_session() as session:
            # === Step 1: Select Event ===
            events = events_crud.get_all_events(session)
            event_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select the event:", view=event_view, ephemeral=True)
            await event_view.wait()
            if not event_view.selected_event_key:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            event = events_crud.get_event_by_key(session, event_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)
    
            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Edit anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send("❌ Edit cancelled.", ephemeral=True)
                force = True
    
            # === Step 2: Select Standalone ActionEvent ===
            standalone_aes = (
                session.query(ActionEvent)
                .join(Action, Action.id == ActionEvent.action_id)
                .filter(
                    ActionEvent.event_id == event.id,
                    ActionEvent.reward_event_id.is_(None),
                    Action.is_active.is_(True),
                )
                .all()
            )
    
            if not standalone_aes:
                return await interaction.followup.send("❌ No standalone action-events to edit.", ephemeral=True)
    
            ae_view = SingleSelectView(ActionEventSelect(standalone_aes))
            await interaction.followup.send("📌 Select the action-event to edit:", view=ae_view, ephemeral=True)
            await ae_view.wait()
            if not ae_view.selected_action_event_key:  
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            ae = action_events_crud.get_action_event_by_key(session, ae_view.selected_action_event_key)
            if not ae:
                return await interaction.followup.send("❌ Invalid action-event.", ephemeral=True)
    
            # === Step 3: Update Points ===
            point_picker = PointPickerView()
            await interaction.followup.send("💠 Choose new point value:", view=point_picker, ephemeral=True)
            await point_picker.wait()
            if point_picker.cancelled:
                return await interaction.followup.send("❌ Cancelled by user.", ephemeral=True)
            if point_picker.custom_points is not None:
                points_granted = point_picker.custom_points
            elif point_picker.selected_points is not None:
                points_granted = point_picker.selected_points
            else:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            # === Step 4: is_allowed_during_visible ===
            allowed_view = ToggleYesNoView("Allow during visible period?")
            await interaction.followup.send(allowed_view.prompt, view=allowed_view, ephemeral=True)
            await allowed_view.wait()
            if allowed_view.value is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            is_allowed_during_visible = allowed_view.value
    
            # === Step 5: is_self_reportable ===
            reportable_view = ToggleYesNoView("Allow self-reporting?")
            await interaction.followup.send(reportable_view.prompt, view=reportable_view, ephemeral=True)
            await reportable_view.wait()
            if reportable_view.value is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            is_self_reportable = reportable_view.value

            # === Step 6: is_repeatable ===
            repeatable_view = ToggleYesNoView("Allow action to be repeated?")
            await interaction.followup.send(repeatable_view.prompt, view=repeatable_view, ephemeral=True)
            await repeatable_view.wait()
            if repeatable_view.value is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            is_repeatable = repeatable_view.value
    
            # === Step 7: Help Text? ===
            # Build fields list based on the linked Action

            linked_action = ae.action
            action_fields = parse_required_fields(linked_action.input_fields_json)
            prefills = parse_help_texts(ae.input_help_json, action_fields)
                
            help_view = HelpTextPerFieldView(fields=action_fields)
            await interaction.followup.send("💬 Add help text? (General + one per selected field)", view=help_view, ephemeral=True)
            await help_view.wait()
            if help_view.help_texts_json is None:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            if help_view.help_texts_json is False:
                input_help_json = ""  # user chose No
            else:
                input_help_json = help_view.help_texts_json  # already JSON string
    
            # === Step 8: Perform Update ===
            iso_now = now_iso()
            updated = action_events_crud.update_action_event(
                session,
                ae.action_event_key,
                {
                    "points_granted": points_granted,
                    "is_allowed_during_visible": is_allowed_during_visible,
                    "is_self_reportable": is_self_reportable,
                    "is_repeatable": is_repeatable,
                    "input_help_json": input_help_json,
                    "modified_by": str(interaction.user.id),
                    "modified_at": iso_now
                },
                force=force
            )
    
            if not updated:
                return await interaction.followup.send("❌ Failed to update action-event.", ephemeral=True)
    
            return await interaction.followup.send(
                f"✅ Updated action-event **{ae.action.action_key}** ({ae.variant}) "
                f"for event **{event.event_name}**.",
                ephemeral=True
            )

    
    # ====== DELETE ACTION EVENT ======
    @admin_or_mod_check()
    @admin_links.command(name="delete_action_event")
    async def delete_action_event(self, interaction: Interaction):
        """Delete a standalone action-event (not linked to a reward)."""
        await interaction.response.defer(ephemeral=True)
        force = False
        msg_timeout = "❌ Action timed out and cancelled."
    
        with db_session() as session:
            # === Step 1: Select Event ===
            events = events_crud.get_all_events(session)
            event_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select the event:", view=event_view, ephemeral=True)
            await event_view.wait()
            if not event_view.selected_event_key:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            event = events_crud.get_event_by_key(session, event_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)
    
            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Delete anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send("❌ Deletion cancelled.", ephemeral=True)
                force = True
    
            # === Step 2: Select Standalone Action-Event ===
            standalone_aes = (
                session.query(ActionEvent)
                .join(Action, Action.id == ActionEvent.action_id)
                .filter(
                    ActionEvent.event_id == event.id,
                    ActionEvent.reward_event_id.is_(None),
                    Action.is_active.is_(True),
                )
                .all()
            )
    
            if not standalone_aes:
                return await interaction.followup.send("❌ No standalone action-events found for this event.", ephemeral=True)
    
            ae_view = SingleSelectView(ActionEventSelect(standalone_aes)) 
            await interaction.followup.send("📌 Select the action-event to delete:", view=ae_view, ephemeral=True)
            await ae_view.wait()
            if not ae_view.selected_action_event_key:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            ae = action_events_crud.get_action_event_by_key(session, ae_view.selected_action_event_key)
            if not ae:
                return await interaction.followup.send("❌ Invalid action-event.", ephemeral=True)

            # === Step 3: Perform Deletion ===
            iso_now = now_iso()
            success = action_events_crud.delete_action_event(
                session,
                ae.action_event_key,
                str(interaction.user.id),
                iso_now,
                force=force
            )
    
            if not success:
                return await interaction.followup.send("❌ Deletion failed.", ephemeral=True)
    
            return await interaction.followup.send(
                f"🗑️ Deleted action-event **{ae.action.action_key}** ({ae.variant}) from **{event.event_name}**.",
                ephemeral=True
            )
    

# ====== SETUP ======
async def setup(bot):
    await bot.add_cog(EventLinksAdminFriendly(bot))
