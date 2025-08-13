# bot/ui/user/report_action_views.py
from __future__ import annotations
import re
import discord
from discord import ui, Interaction, TextStyle  

from bot.ui.common.selects import GenericSelectView, build_select_options_from_vms
from bot.presentation.user_actions_presentation import ActionOptionVM, get_event_pick_vms, get_event_and_action_vms, submit_report_action_presentation, build_action_report_success_message
from bot.services.prompts_service import set_user_action_prompts

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

            msg = build_action_report_success_message(result)
            await inter.response.send_message(msg, ephemeral=True)
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

        valid_fields = {"url_value", "numeric_value", "text_value", "boolean_value", "date_value"}
        valid_inputs = [f for f in vm.input_fields if f in valid_fields]

        if not valid_inputs:
            raise ValueError(f"[Modal Error] No valid input fields found: {vm.input_fields}")

        for f in valid_inputs:
            help_text = (vm.input_help_map or {}).get(f, "")
            if f == "url_value":
                comp = ui.TextInput(label="URL", placeholder=help_text or "https://…", required=True, max_length=4000)
            elif f == "numeric_value":
                comp = ui.TextInput(label="Number", placeholder=help_text or "Integer ≥ 0", required=True, max_length=20)
            elif f == "text_value":
                comp = ui.TextInput(label="Text", placeholder=help_text or "Text", required=True, style=TextStyle.paragraph, max_length=4000)
            elif f == "boolean_value":
                comp = ui.TextInput(label="Yes/No", placeholder=help_text or "yes / no", required=True, max_length=10)
            elif f == "date_value":
                comp = ui.TextInput(label="Date", placeholder=help_text or "YYYY-MM-DD", required=True, max_length=10)
            else:
                continue
            self.add_item(comp)
            self.inputs[f] = comp

    async def on_submit(self, interaction: Interaction):
        try:
            url = num = txt = boo = dat = None
    
            if "url_value" in self.inputs:
                v = self.inputs["url_value"].value.strip()
                if not (v.startswith("http://") or v.startswith("https://")):
                    await interaction.response.send_message("⚠️ Please enter a valid URL (http/https).", ephemeral=True)
                    return
                url = v
    
            if "numeric_value" in self.inputs:
                raw = self.inputs["numeric_value"].value.strip()
                try:
                    n = int(raw)
                    if n < 0:
                        raise ValueError()
                    num = n
                except Exception:
                    await interaction.response.send_message("⚠️ The number must be an integer ≥ 0.", ephemeral=True)
                    return
    
            if "text_value" in self.inputs:
                txt = self.inputs["text_value"].value.strip() or None
    
            if "boolean_value" in self.inputs:
                raw = self.inputs["boolean_value"].value.strip().lower()
                if raw in {"yes", "y", "true", "1"}:
                    boo = True
                elif raw in {"no", "n", "false", "0"}:
                    boo = False
                else:
                    await interaction.response.send_message("⚠️ For Yes/No, type yes or no.", ephemeral=True)
                    return
    
            if "date_value" in self.inputs:
                raw = self.inputs["date_value"].value.strip()
                if not re.match(r"^\\d{4}-\\d{2}-\\d{2}$", raw):
                    await interaction.response.send_message("⚠️ Date must be YYYY-MM-DD.", ephemeral=True)
                    return
                dat = raw
    
            result = submit_report_action_presentation(
                interaction.user,
                action_event_id=self.action_event_id,
                url_value=url, numeric_value=num, text_value=txt,
                boolean_value=boo, date_value=dat,
            )
    
            if isinstance(result, str):
                await interaction.response.send_message(result, ephemeral=True)
                return
    
            if result is None:
                await interaction.response.send_message("❌ Unexpected error while saving the report.", ephemeral=True)
                return
    
            from bot.presentation.user_actions_presentation import build_action_report_success_message
    
            # 🧩 Handle prompt case if required
            if self.vm.prompts_required:
                from bot.services.prompts_service import picker_prompts_for_action_event
                prompts = picker_prompts_for_action_event(self.action_event_id)
    
                if prompts:
                    from bot.ui.user.report_action_views import PromptPaginatedView
                    await interaction.response.send_message(
                        content="📝 Select which prompt(s) this submission covers:",
                        view=PromptPaginatedView(user_action_id=result.user_action_id, prompts=prompts, result=result),
                        ephemeral=True
                    )
                    return
    
            # ✅ Fallback: success message
            msg = build_action_report_success_message(result)
            await interaction.response.send_message(msg, ephemeral=True)
    
        except Exception as e:
            print(f"[Modal] UNHANDLED ERROR: {e}")
            try:
                await interaction.response.send_message("❌ Fatal error occurred.", ephemeral=True)
            except:
                pass


class PromptGroupSelect(discord.ui.Select):
    def __init__(self, parent_view: PromptPaginatedView):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(label="All groups", value="all", default=(parent_view.group is None))
        ]
        for g in parent_view.available_groups:
            label = g.capitalize() if g != "default" else "Ungrouped"
            options.append(
                discord.SelectOption(
                    label=label,
                    value=g,
                    default=(parent_view.group == g)
                )
            )

        super().__init__(
            placeholder="Filter by prompt group…",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.group = self.values[0]
        self.parent_view.page = 0
        self.parent_view._refresh_select()
        await interaction.response.edit_message(view=self.parent_view)

class PromptPaginatedView(discord.ui.View):
    def __init__(self, user_action_id: int, prompts: list, result: ActionReportResultDTO, *, per_page: int = 25):
        super().__init__(timeout=300)
        self.user_action_id = user_action_id
        self.all_prompts = prompts
        self.result = result  # ✅ new
        self.per_page = per_page
        self.page = 0
        self.group: str | None = None
        self.selected_ids: set[int] = set()

        self.available_groups = sorted({p.group or "default" for p in prompts})
        self._refresh_select()

    def _get_filtered_prompts(self):
        if not self.group or self.group == "all":
            return self.all_prompts
        return [p for p in self.all_prompts if (p.group or "default") == self.group]

    def _refresh_select(self):
        self.clear_items()

        filtered = self._get_filtered_prompts()
        start = self.page * self.per_page
        end = start + self.per_page
        current = filtered[start:end]

        # Row 0: Live selection count label
        label_button = discord.ui.Button(
            label=f"📝 {len(self.selected_ids)} prompt(s) selected",
            disabled=True,
            style=discord.ButtonStyle.secondary,
            row=0
        )
        self.add_item(label_button)

        # Row 1: Group filter (if applicable)
        if self.available_groups and len(self.available_groups) > 1:
            group_select = PromptGroupSelect(self)
            group_select.row = 1
            self.add_item(group_select)
            select_row = 2
        else:
            select_row = 1

        if not current:
            print("[PromptPaginatedView] No prompts to display on this page")
            return

        # Prompt multi-select
        try:
            options = [
                discord.SelectOption(
                    label=p.label[:100],
                    value=str(p.id),
                    description=f"#{p.code}" if p.code else None,
                    default=(p.id in self.selected_ids)
                ) for p in current
            ]
        except Exception as e:
            print(f"[PromptPaginatedView] Error building select options: {e}")
            return

        select = discord.ui.Select(
            placeholder=f"Page {self.page + 1} — Select prompts",
            options=options,
            min_values=0,
            max_values=min(25, len(options)),
            row=select_row
        )
        select.callback = self.on_prompt_select
        self.add_item(select)

        # Row 3: Navigation and submit buttons
        nav_row = 3
        if self.page > 0:
            btn = PrevPageButton(self)
            btn.row = nav_row
            self.add_item(btn)
        if (self.page + 1) * self.per_page < len(filtered):
            btn = NextPageButton(self)
            btn.row = nav_row
            self.add_item(btn)

        submit_btn = SubmitButton(self)
        submit_btn.row = nav_row
        self.add_item(submit_btn)

    async def on_prompt_select(self, interaction: discord.Interaction):
        values = [int(v) for v in interaction.data["values"]]

        # Replace selections for current page only
        filtered = self._get_filtered_prompts()
        start = self.page * self.per_page
        end = start + self.per_page
        current_ids = {p.id for p in filtered[start:end]}

        self.selected_ids.difference_update(current_ids)
        self.selected_ids.update(values)

        try:
            self._refresh_select()
            await interaction.response.edit_message(view=self)
        except Exception as e:
            print(f"[PromptPaginatedView] Silent edit failed: {e}")
            await interaction.response.send_message("⚠️ Prompt selection registered.", ephemeral=True)

class SubmitButton(discord.ui.Button):
    def __init__(self, view: PromptPaginatedView):
        super().__init__(label="✅ Submit Selection", style=discord.ButtonStyle.success, row=3)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        view = self.view_ref

        selected = [p for p in view.all_prompts if p.id in view.selected_ids]
        summary_lines = [f"• {p.label} ({p.code})" for p in selected]
        summary_text = "\n".join(summary_lines) or "_(none)_"

        try:
            set_user_action_prompts(
                user_action_id=view.user_action_id,
                event_prompt_ids=list(view.selected_ids)
            )
            msg = build_action_report_success_message(view.result)
            msg += f"\n\n📝 You selected **{len(selected)} prompt(s)** for this action:\n{summary_text}"
            await interaction.response.edit_message(content=msg, view=None)
        except Exception:
            await interaction.response.send_message("❌ Could not save prompts.", ephemeral=True)

class PrevPageButton(discord.ui.Button):
    def __init__(self, view: PromptPaginatedView):
        super().__init__(label="◀ Previous", style=discord.ButtonStyle.secondary, row=2)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        view = self.view_ref
        view.page = max(view.page - 1, 0)
        view._refresh_select()
        await interaction.response.edit_message(view=view)

class NextPageButton(discord.ui.Button):
    def __init__(self, view: PromptPaginatedView):
        super().__init__(label="Next ▶", style=discord.ButtonStyle.secondary, row=2)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        view = self.view_ref
        max_page = (len(view._get_filtered_prompts()) - 1) // view.per_page
        view.page = min(view.page + 1, max_page)
        view._refresh_select()
        await interaction.response.edit_message(view=view)