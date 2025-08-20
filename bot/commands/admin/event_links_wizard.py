# bot/commands/admin/event_links_wizard.py
import discord
from discord.ext import commands
from discord import app_commands
from bot.utils.time_parse_paginate import admin_or_mod_check, now_iso
from db.database import db_session
from db.schema import RewardEvent, ActionEvent, Action
from bot.crud import events_crud, rewards_crud, reward_events_crud, actions_crud, action_events_crud, event_triggers_crud
from bot.utils.time_parse_paginate import parse_required_fields, parse_help_texts
from bot.config.constants import CURRENCY
from bot.ui.admin.event_link_views import (
    EventSelect, RewardSelect, RewardEventSelect, AvailabilitySelect, PricePicker, ForceConfirmView, ActionEventSelect,
    ActionSelect, VariantPickerView, HelpTextPerFieldView, YesNoView, ToggleYesNoView,
    SingleSelectView, PointPickerView, PromptGroupModal
)
# ----------------------------
# Local light-weight selects
# ----------------------------
class TargetTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Action", value="action", description="Configure an ActionEvent (points and/or reward)"),
            discord.SelectOption(label="Trigger", value="trigger", description="Configure a Trigger (points and/or reward)"),
            discord.SelectOption(label="Shop", value="shop", description="Put rewards in shop (price)"),
        ]
        super().__init__(placeholder="Choose what to configure…", min_values=1, max_values=1, options=options)
        self.selected = None

    async def callback(self, interaction: discord.Interaction):
        self.selected = self.values[0]
        await interaction.response.edit_message(content=f"Selected **{self.selected}**.", view=None)

class TriggerSelect(discord.ui.Select):
    def __init__(self, triggers):
        # triggers: list of objects with id + ui_label
        options = [
            discord.SelectOption(label=(t.ui_label or f"Trigger #{t.id}")[:100], value=str(t.id))
            for t in triggers
        ]
        super().__init__(placeholder="Pick a trigger…", min_values=1, max_values=1, options=options)
        self.selected_id = None

    async def callback(self, interaction: discord.Interaction):
        self.selected_id = int(self.values[0])
        await interaction.response.edit_message(content="Trigger selected.", view=None)

# A tiny wrapper to reuse your SingleSelectView pattern
class _SingleSelect(discord.ui.View):
    def __init__(self, inner_select: discord.ui.Select, *, timeout=180):
        super().__init__(timeout=timeout)
        self._select = inner_select
        self.add_item(inner_select)

    @property
    def result(self):
        # convenience to read selected value(s)
        if isinstance(self._select, TargetTypeSelect):
            return self._select.selected
        if isinstance(self._select, TriggerSelect):
            return self._select.selected_id
        # generic cases from your existing Selects:
        # EventSelect -> selected_event_key, RewardSelect -> selected_reward_key, etc.
        # Those are handled by your existing SingleSelectView

# ----------------------------
# Service-ish helpers (no schema changes)
# ----------------------------
def _ensure_reward_event(session, event, reward, availability: str, price: int, actor_id: str):
    """Create or fetch RewardEvent for (event, reward, availability)."""
    re_key = f"{event.event_key.lower()}_{reward.reward_key.lower()}_{availability}"
    existing = reward_events_crud.get_reward_event_by_key(session, re_key)
    if existing:
        if availability == "inshop" and existing.price != price:
            reward_events_crud.update_reward_event(session, re_key, {
                "price": price,
                "modified_by": actor_id,
                "modified_at": now_iso(),
            }, force=True)
        return existing

    return reward_events_crud.create_reward_event(session, {
        "reward_event_key": re_key,
        "reward_id": reward.id,
        "event_id": event.id,
        "availability": availability,
        "price": price,
        "created_by": actor_id,
        "created_at": now_iso()
    }, force=True)

def _attach_reward_to_action_event(session, ae_key: str, reward_event_id: int, actor_id: str):
    return action_events_crud.update_action_event(session, ae_key, {
        "reward_event_id": reward_event_id,
        "modified_by": actor_id,
        "modified_at": now_iso()
    }, force=True)

def _set_points_for_action_event(session, ae_key: str, points: int | None, actor_id: str):
    return action_events_crud.update_action_event(session, ae_key, {
        "points_granted": points,
        "modified_by": actor_id,
        "modified_at": now_iso()
    }, force=True)

def _attach_reward_to_trigger(session, trigger_id: int, reward_event_id: int, actor_id: str):
    # TODO: adjust fields to your actual trigger model
    return event_triggers_crud.update_event_trigger(session, trigger_id, {
        "reward_event_id": reward_event_id,
        "modified_by": actor_id,
        "modified_at": now_iso()
    }, force=True)

def _set_points_for_trigger(session, trigger_id: int, points: int | None, actor_id: str):
    # TODO: adjust fields to your actual trigger model
    return event_triggers_crud.update_event_trigger(session, trigger_id, {
        "points_granted": points,
        "modified_by": actor_id,
        "modified_at": now_iso()
    }, force=True)

def _get_reward_access_paths(session, event_id: int, reward_id: int):
    """Return a list of dicts describing how the reward is currently reachable in this event."""
    paths = []
    res = session.query(RewardEvent).filter_by(event_id=event_id, reward_id=reward_id).all()
    for re in res:
        if re.availability == "inshop":
            paths.append({"availability": "inshop", "price": re.price})
        elif re.availability == "onaction":
            aes = session.query(ActionEvent).filter_by(reward_event_id=re.id).all()
            for ae in aes:
                paths.append({"availability": "onaction", "action_event_key": ae.action_event_key})
        elif re.availability == "ontrigger":
            # TODO: you may want a dedicated query helper for this
            tgs = event_triggers_crud.get_triggers_for_reward_event(session, re.id)  # returns list with .ui_label
            for t in tgs:
                paths.append({"availability": "ontrigger", "trigger_label": getattr(t, "ui_label", f"Trigger #{t.id}")})
    return paths

def _fmt_conflicts(paths: list[dict], currency_symbol: str) -> str:
    if not paths:
        return "No other access paths."
    bits = []
    for p in paths:
        if p["availability"] == "inshop":
            bits.append(f"in shop ({p.get('price', 0)} {currency_symbol})")
        elif p["availability"] == "onaction":
            bits.append(f"on action `{p.get('action_event_key')}`")
        elif p["availability"] == "ontrigger":
            bits.append(f"on trigger “{p.get('trigger_label', 'Trigger')}”")
    return "Already available: " + ", ".join(bits)

# -----------------------------------
# The single wizard command
# -----------------------------------
class AdminEventLinkWizardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @admin_or_mod_check()
    @app_commands.command(name="configure_payouts", description="One place to wire Actions, Triggers, or Shop with points/rewards.")
    async def configure_payouts(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        msg_timeout = "❌ Action timed out and cancelled."
        actor_id = str(interaction.user.id)
    
        with db_session() as session:
            # 1) Pick event
            events = events_crud.get_all_events(session)
            if not events:
                return await interaction.followup.send("❌ No events found.", ephemeral=True)
            ev_view = SingleSelectView(EventSelect(events))
            await interaction.followup.send("📌 Select the event:", view=ev_view, ephemeral=True)
            await ev_view.wait()
            if not ev_view.selected_event_key:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
    
            event = events_crud.get_event_by_key(session, ev_view.selected_event_key)
            if not event:
                return await interaction.followup.send("❌ Invalid event.", ephemeral=True)
    
            # If active, confirm (matches your pattern)
            if events_crud.is_event_active(session, event.id):
                confirm_view = ForceConfirmView(f"⚠️ **{event.event_name}** is active. Configure anyway?")
                await interaction.followup.send(confirm_view.prompt, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    return await interaction.followup.send("❌ Cancelled.", ephemeral=True)
    
            # 2) Pick target type
            tsel = _SingleSelect(TargetTypeSelect())
            await interaction.followup.send("🎯 What do you want to configure?", view=tsel, ephemeral=True)
            await tsel.wait()
            if not tsel.result:
                return await interaction.followup.send(msg_timeout, ephemeral=True)
            target_type = tsel.result  # "action" | "trigger" | "shop"
    
            # ---------------- ACTION path ----------------
            if target_type == "action":
                # Select an active action
                active_actions = [a for a in actions_crud.get_all_actions(session) if a.is_active]
                if not active_actions:
                    return await interaction.followup.send("❌ No active actions.", ephemeral=True)
                a_view = SingleSelectView(ActionSelect(active_actions))
                await interaction.followup.send("🧩 Select the action:", view=a_view, ephemeral=True)
                await a_view.wait()
                if not a_view.selected_action_key:
                    return await interaction.followup.send(msg_timeout, ephemeral=True)
                action = actions_crud.get_action_by_key(session, a_view.selected_action_key)
    
                # Variant (creates ActionEvent if new)
                vp = VariantPickerView()
                await interaction.followup.send("🔠 Select or type a variant:", view=vp, ephemeral=True)
                await vp.wait()
                if not vp.selected_variant:
                    return await interaction.followup.send(msg_timeout, ephemeral=True)
                variant = vp.selected_variant
                variant_clean = variant.strip().lower().replace(" ", "_")
                ae_key = f"{event.event_key.lower()}_{action.action_key.lower()}_{variant_clean}"
    
                ae_existing = action_events_crud.get_action_event_by_key(session, ae_key)
                if not ae_existing:
                    # minimal creation path; your full standalone flow is heavier, this keeps the wizard snappy
                    action_fields = parse_required_fields(action.input_fields_json)
                    help_view = HelpTextPerFieldView(fields=action_fields)
                    await interaction.followup.send("💬 Add help text? (General + per-field; or choose 'No')", view=help_view, ephemeral=True)
                    await help_view.wait()
                    if help_view.help_texts_json is None:
                        return await interaction.followup.send(msg_timeout, ephemeral=True)
                    input_help_json = "" if help_view.help_texts_json is False else help_view.help_texts_json
    
                    # toggles consistent with your other commands
                    allowed_view = ToggleYesNoView("Allow during visible period?")
                    reportable_view = ToggleYesNoView("Allow self-report?")
                    repeatable_view = ToggleYesNoView("Allow repeats?")
                    mult_view = ToggleYesNoView("Treat numeric value as multiplier?")
                    prompts_view = ToggleYesNoView("Use prompt selection?")
    
                    for v in (allowed_view, reportable_view, repeatable_view, mult_view, prompts_view):
                        await interaction.followup.send(v.prompt, view=v, ephemeral=True)
                        await v.wait()
                        if v.value is None:
                            return await interaction.followup.send(msg_timeout, ephemeral=True)
    
                    action_events_crud.create_action_event(session, {
                        "action_event_key": ae_key,
                        "action_id": action.id,
                        "event_id": event.id,
                        "variant": variant,
                        "points_granted": 0,
                        "is_allowed_during_visible": allowed_view.value,
                        "is_self_reportable": reportable_view.value,
                        "is_repeatable": repeatable_view.value,
                        "input_help_json": input_help_json,
                        "reward_event_id": None,
                        "is_numeric_multiplier": mult_view.value,
                        "prompts_required": prompts_view.value,
                        "created_by": actor_id,
                        "created_at": now_iso()
                    }, force=True)
    
                # Choose to give points?
                give_points = ToggleYesNoView("Give points for this action?")
                await interaction.followup.send(give_points.prompt, view=give_points, ephemeral=True)
                await give_points.wait()
                points = None
                if give_points.value:
                    pp = PointPickerView()
                    await interaction.followup.send("💠 Pick point value:", view=pp, ephemeral=True)
                    await pp.wait()
                    if pp.cancelled:
                        return await interaction.followup.send("❌ Cancelled.", ephemeral=True)
                    points = pp.custom_points if pp.custom_points is not None else pp.selected_points
                    _set_points_for_action_event(session, ae_key, points, actor_id)
    
                # Choose to attach a reward?
                give_reward = ToggleYesNoView("Attach a reward to this action?")
                await interaction.followup.send(give_reward.prompt, view=give_reward, ephemeral=True)
                await give_reward.wait()
                reward_str = "—"
                if give_reward.value:
                    # pick reward
                    all_rewards = rewards_crud.get_all_rewards(session)
                    r_view = SingleSelectView(RewardSelect(all_rewards))
                    await interaction.followup.send("🎁 Select reward to attach:", view=r_view, ephemeral=True)
                    await r_view.wait()
                    if not r_view.selected_reward_key:
                        return await interaction.followup.send(msg_timeout, ephemeral=True)
                    reward = rewards_crud.get_reward_by_key(session, r_view.selected_reward_key)
                    re_onaction = _ensure_reward_event(session, event, reward, "onaction", 0, actor_id)
                    _attach_reward_to_action_event(session, ae_key, re_onaction.id, actor_id)
                    reward_str = reward.reward_name
    
                    # conflicts
                    paths = _get_reward_access_paths(session, event.id, reward.id)
                    conflicts = _fmt_conflicts(paths, CURRENCY)
                    await interaction.followup.send(f"⚠️ {conflicts}", ephemeral=True)
    
                return await interaction.followup.send(
                    f"✅ **Action wired.** `{action.action_key}` ({variant})"
                    f"\n• Points: {points if points is not None else '—'}"
                    f"\n• Reward: {reward_str}",
                    ephemeral=True
                )
    
            # ---------------- TRIGGER path ----------------
            if target_type == "trigger":
                # TODO: replace with your real fetch for triggers of this event
                triggers = event_triggers_crud.get_event_triggers_for_event(session, event.id)  # expects .id, .ui_label
                if not triggers:
                    return await interaction.followup.send("❌ No triggers found for this event.", ephemeral=True)
    
                tv = _SingleSelect(TriggerSelect(triggers))
                await interaction.followup.send("🧨 Pick a trigger:", view=tv, ephemeral=True)
                await tv.wait()
                if not tv.result:
                    return await interaction.followup.send(msg_timeout, ephemeral=True)
                trigger_id = tv.result
    
                # points?
                give_points = ToggleYesNoView("Give points for this trigger?")
                await interaction.followup.send(give_points.prompt, view=give_points, ephemeral=True)
                await give_points.wait()
                t_points = None
                if give_points.value:
                    pp = PointPickerView()
                    await interaction.followup.send("💠 Pick point value:", view=pp, ephemeral=True)
                    await pp.wait()
                    if pp.cancelled:
                        return await interaction.followup.send("❌ Cancelled.", ephemeral=True)
                    t_points = pp.custom_points if pp.custom_points is not None else pp.selected_points
                    _set_points_for_trigger(session, trigger_id, t_points, actor_id)
    
                # reward?
                give_reward = ToggleYesNoView("Attach a reward to this trigger?")
                await interaction.followup.send(give_reward.prompt, view=give_reward, ephemeral=True)
                await give_reward.wait()
                t_reward_str = "—"
                if give_reward.value:
                    all_rewards = rewards_crud.get_all_rewards(session)
                    r_view = SingleSelectView(RewardSelect(all_rewards))
                    await interaction.followup.send("🎁 Select reward to attach:", view=r_view, ephemeral=True)
                    await r_view.wait()
                    if not r_view.selected_reward_key:
                        return await interaction.followup.send(msg_timeout, ephemeral=True)
                    reward = rewards_crud.get_reward_by_key(session, r_view.selected_reward_key)
                    re_ontrigger = _ensure_reward_event(session, event, reward, "ontrigger", 0, actor_id)
                    _attach_reward_to_trigger(session, trigger_id, re_ontrigger.id, actor_id)
                    t_reward_str = reward.reward_name
    
                    # conflicts
                    paths = _get_reward_access_paths(session, event.id, reward.id)
                    conflicts = _fmt_conflicts(paths, CURRENCY)
                    await interaction.followup.send(f"⚠️ {conflicts}", ephemeral=True)
    
                return await interaction.followup.send(
                    f"✅ **Trigger wired.**"
                    f"\n• Points: {t_points if t_points is not None else '—'}"
                    f"\n• Reward: {t_reward_str}",
                    ephemeral=True
                )
    
            # ---------------- SHOP path ----------------
            if target_type == "shop":
                # pick reward (single for now; easy to extend to multi)
                all_rewards = rewards_crud.get_all_rewards(session)
                if not all_rewards:
                    return await interaction.followup.send("❌ No rewards found.", ephemeral=True)
                r_view = SingleSelectView(RewardSelect(all_rewards))
                await interaction.followup.send("🛒 Select reward to put in shop:", view=r_view, ephemeral=True)
                await r_view.wait()
                if not r_view.selected_reward_key:
                    return await interaction.followup.send(msg_timeout, ephemeral=True)
                reward = rewards_crud.get_reward_by_key(session, r_view.selected_reward_key)
    
                # price
                price_picker = PricePicker()
                await interaction.followup.send("💰 Set price:", view=price_picker, ephemeral=True)
                await price_picker.wait()
                if price_picker.selected_price is None:
                    return await interaction.followup.send(msg_timeout, ephemeral=True)
                price = price_picker.selected_price
    
                re_inshop = _ensure_reward_event(session, event, reward, "inshop", price, actor_id)
    
                # conflicts
                paths = _get_reward_access_paths(session, event.id, reward.id)
                conflicts = _fmt_conflicts(paths, CURRENCY)
                await interaction.followup.send(f"⚠️ {conflicts}", ephemeral=True)
    
                return await interaction.followup.send(
                    f"✅ **Shop wired.**"
                    f"\n• Reward: {reward.reward_name}"
                    f"\n• Price: {price} {CURRENCY}",
                    ephemeral=True
                )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminEventLinkWizardCog(bot))