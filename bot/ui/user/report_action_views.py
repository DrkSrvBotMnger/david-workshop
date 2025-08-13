# bot/ui/user/report_action_views.py
from __future__ import annotations
import re
import discord
from discord import ui, Interaction, TextStyle  

from bot.ui.common.selects import GenericSelectView, build_select_options_from_vms
from bot.presentation.user_actions_presentation import ActionOptionVM, get_event_pick_vms, get_event_and_action_vms, submit_report_action_presentation

# ----------------------- Event picker (reusable builder) -----------------------

def make_event_select_view(owner_id: int) -> discord.ui.View | None:
    """
    Build the event select view using our common GenericSelectView.
    Returns None if there are zero options (avoid empty Select -> 400).
    """
    event_vms = get_event_pick_vms(limit=25)
    options = build_select_options_from_vms(
        event_vms,
        get_value=lambda vm: vm.value,
        get_label=lambda vm: vm.label,
        get_description=lambda vm: vm.description,
        limit=25,
    )

    async def on_event_selected(inter: Interaction, event_key: str):
        if inter.user.id != owner_id:
            await inter.response.send_message("⛔ You can’t use this menu.", ephemeral=True)
            return

        ev_vm, action_vms = get_event_and_action_vms(inter.user, event_key)

        if ev_vm is None:
            await inter.response.edit_message(content="❌ Event not found.", view=None)
            return

        if not action_vms:
            new_view = make_event_select_view(owner_id)
            if new_view is None:
                await inter.response.edit_message(
                    content=f"⚠️ No actions available for **{ev_vm.name}**.\nTry again later.",
                    view=None
                )
            else:
                await inter.response.edit_message(
                    content=f"⚠️ No actions available for **{ev_vm.name}**.\nPick another event:",
                    view=new_view
                )
            return

        action_view = make_action_select_view(owner_id, ev_vm.id, action_vms)
        await inter.response.edit_message(
            content=f"📝 **{ev_vm.name}** — choose an action to report:",
            view=action_view
        )

    return GenericSelectView(
        options=options,
        on_select=on_event_selected,
        placeholder="Select an event…",
        timeout=180,
    )

# ----------------------- Action picker (reusable builder) -----------------------

def make_action_select_view(owner_id: int, event_id: int, actions: list[ActionOptionVM]) -> discord.ui.View:
    options = build_select_options_from_vms(
        actions,
        get_value=lambda vm: vm.id,
        get_label=lambda vm: vm.label[:100],
        get_description=lambda vm: (vm.description or "")[:100],
        limit=25,
    )

    async def on_action_selected(inter: Interaction, value: str):
        if inter.user.id != owner_id:
            await inter.response.send_message("⛔ You can’t use this menu.", ephemeral=True)
            return

        try:
            action_event_id = int(value)
        except Exception:
            await inter.response.send_message("❌ Action not found.", ephemeral=True)
            return

        vm = next((a for a in actions if a.id == action_event_id), None)
        if not vm:
            await inter.response.send_message("❌ Action not found.", ephemeral=True)
            return

        if not vm.input_fields:
            try:
                result = submit_report_action_presentation(
                    inter.user,
                    action_event_id=action_event_id,
                    url_value=None, numeric_value=None, text_value=None,
                    boolean_value=None, date_value=None,
                )
            except Exception as e:
                print(f"[ActionSelect] immediate submit error: {e}")
                await inter.response.send_message("❌ Error while saving.", ephemeral=True)
                return

            if isinstance(result, str):
                await inter.response.send_message(result, ephemeral=True)
                return

            parts = []
            if result.reward_name: parts.append(f"🏆 **{result.reward_name}**")
            if result.points_awarded: parts.append(f"+{result.points_awarded} :coin:")
            head = " • ".join(parts) or "✅ Action recorded."

            details = []
            if result.numeric_value is not None: details.append(f"Count: `{result.numeric_value}`")
            if result.url_value: details.append(f"URL: <{result.url_value}>")
            if result.text_value: details.append(f"Text: {result.text_value[:200]}")
            if result.boolean_value is not None: details.append(f"Yes/No: {'yes' if result.boolean_value else 'no'}")
            if result.date_value: details.append(f"Date: {result.date_value}")

            desc = f"**{result.action_label}** in **{result.event_name}**\n" + ("\n".join(details) if details else "")
            await inter.response.send_message(f"{head}\n{desc}", ephemeral=True)
            return

        try:
            await inter.response.send_modal(ReportActionModal(action_event_id, vm))
        except Exception as e:
            print(f"[ActionSelect] send_modal error: {e}")
            await inter.followup.send("❌ Couldn’t open the form.", ephemeral=True)

    return GenericSelectView(
        options=options,
        on_select=on_action_selected,
        placeholder="Select an action…",
        timeout=180,
    )

# ----------------------- Modal -----------------------

class ReportActionModal(ui.Modal, title="Report an action"):
    def __init__(self, action_event_id: int, vm):
        super().__init__()
        self.action_event_id = action_event_id
        self.vm = vm
        self.inputs: dict[str, ui.TextInput] = {}

        for f in vm.input_fields:
            help_text = (vm.input_help_map or {}).get(f, "")
            if f == "url":
                comp = ui.TextInput(
                    label="URL",
                    placeholder=help_text or "https://…",
                    required=True,
                    max_length=4000,
                )
            elif f == "numeric_value":
                comp = ui.TextInput(
                    label="Number",
                    placeholder=help_text or "Integer ≥ 0",
                    required=True,
                    max_length=20,
                )
            elif f == "text_value":
                comp = ui.TextInput(
                    label="Text",
                    placeholder=help_text or "Text",
                    required=True,
                    style=TextStyle.paragraph,
                    max_length=4000,
                )
            elif f == "boolean_value":
                comp = ui.TextInput(
                    label="Yes/No",
                    placeholder=help_text or "yes / no",
                    required=True,
                    max_length=10,
                )
            elif f == "date_value":
                comp = ui.TextInput(
                    label="Date",
                    placeholder=help_text or "YYYY-MM-DD",
                    required=True,
                    max_length=10,
                )
            else:
                continue

            self.add_item(comp)
            self.inputs[f] = comp

    async def on_submit(self, interaction: Interaction):
        
        url = num = txt = boo = dat = None

        if "url" in self.inputs:
            v = (self.inputs["url"].value or "").strip()
            if not (v.startswith("http://") or v.startswith("https://")):
                await interaction.response.send_message("⚠️ Please enter a valid URL (http/https).", ephemeral=True)
                return
            url = v

        if "numeric_value" in self.inputs:
            raw = (self.inputs["numeric_value"].value or "").strip()
            try:
                n = int(raw)
                if n < 0:
                    raise ValueError()
            except Exception:
                await interaction.response.send_message("⚠️ The number must be an integer ≥ 0.", ephemeral=True)
                return
            num = n

        if "text_value" in self.inputs:
            txt = (self.inputs["text_value"].value or "").strip() or None

        if "boolean_value" in self.inputs:
            raw = (self.inputs["boolean_value"].value or "").strip().lower()
            if raw in {"yes", "y", "true", "1"}:
                boo = True
            elif raw in {"no", "n", "false", "0"}:
                boo = False
            else:
                await interaction.response.send_message("⚠️ For Yes/No, type yes or no.", ephemeral=True)
                return

        if "date_value" in self.inputs:
            raw = (self.inputs["date_value"].value or "").strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
                await interaction.response.send_message("⚠️ Date must be YYYY-MM-DD.", ephemeral=True)
                return
            dat = raw

        try:
            from bot.presentation.user_actions_presentation import submit_report_action_presentation
            result = submit_report_action_presentation(
                interaction.user,
                action_event_id=self.action_event_id,
                url_value=url, numeric_value=num, text_value=txt,
                boolean_value=boo, date_value=dat,
            )
        except Exception as e:
            print(f"[ReportActionModal] submit error: {e}")
            await interaction.response.send_message("❌ Error while saving.", ephemeral=True)
            return

        if isinstance(result, str):
            await interaction.response.send_message(result, ephemeral=True)
            return

        parts = []
        if result.reward_name: parts.append(f"🏆 **{result.reward_name}**")
        if result.points_awarded: parts.append(f"+{result.points_awarded} :coin:")
        head = " • ".join(parts) or "✅ Action recorded."

        details = []
        if result.numeric_value is not None: details.append(f"Count: `{result.numeric_value}`")
        if result.url_value: details.append(f"URL: <{result.url_value}>")
        if result.text_value: details.append(f"Text: {result.text_value[:200]}")
        if result.boolean_value is not None: details.append(f"Yes/No: {'yes' if result.boolean_value else 'no'}")
        if result.date_value: details.append(f"Date: {result.date_value}")

        desc = f"**{result.action_label}** in **{result.event_name}**\n" + ("\n".join(details) if details else "")
        await interaction.response.send_message(f"{head}\n{desc}", ephemeral=True)