# bot/ui/admin/event_triggers_views.py
import discord

class ConfigModal(discord.ui.Modal):
    def __init__(self, trigger_type, prefill=None):
        super().__init__(title=f"Configure Trigger ({trigger_type})")
        self.fields = {}
        self.numeric_keys = set()
        self.prefill = prefill or {}

        def add_field(key: str, label: str, required: bool = True, numeric: bool = False):
            default = str(prefill.get(key, "")) if prefill else ""
            field = discord.ui.TextInput(
                label=label,
                default=default,
                required=required,
                style=discord.TextStyle.short,
                placeholder="Enter a number" if numeric else None,
            )
            self.add_item(field)
            self.fields[key] = field
            if numeric:
                self.numeric_keys.add(key)

        if trigger_type == "prompt_count":
            add_field("min_count", "Minimum prompts in one report", numeric=True)

        elif trigger_type == "prompt_unique":
            add_field("min_count", "Minimum number of different prompts", numeric=True)

        elif trigger_type == "prompt_repeat":
            add_field("prompt_code", "Prompt code (informative - do not edit)")
            add_field("min_count", "Times", numeric=True)

        elif trigger_type == "streak":
            add_field("min_days", "Consecutive participation days", numeric=True)

        elif trigger_type == "event_count":
            add_field("min_reports", "Number of actions submitted", numeric=True)

        elif trigger_type == "action_repeat":
            add_field("action_event_id", "ActionEvent ID (informative - do not edit)")
            add_field("min_count", "Times", numeric=True)

        elif trigger_type == "points_won":
            add_field("min_points", "Points earned", numeric=True)

        elif trigger_type == "participation_days":
            add_field("min_days", "Number of days participated", numeric=True)

        elif trigger_type == "global_count":
            add_field("min_reports", "Number of actions (global)", numeric=True)

        elif trigger_type == "global_points_won":
            add_field("min_points", "Points earned (global)", numeric=True)

        else:
            add_field("info", "Custom config (JSON)", required=False)

        self.invalid_numeric = None  # Track error field

    async def on_submit(self, interaction: discord.Interaction):
        # Validation: make sure numeric fields are valid integers ≥ 0
        for key in self.numeric_keys:
            val = self.fields[key].value.strip()
            try:
                if int(val) < 0:
                    raise ValueError()
            except Exception:
                self.invalid_numeric = key
                await interaction.response.send_message(
                    f"⚠️ **{self.fields[key].label}** must be an integer ≥ 0.",
                    ephemeral=True
                )
                return

        await interaction.response.defer()  # Modal will close silently

    def get_config(self) -> dict:
        config = {}

        # Add fields from the modal
        for key, field in self.fields.items():
            raw = field.value.strip()
            if key in self.numeric_keys:
                config[key] = int(raw)
            else:
                config[key] = raw

        # Also include any prefill keys not handled via modal fields
        if hasattr(self, "prefill") and self.prefill:
            for key, value in self.prefill.items():
                if key not in config:
                    config[key] = value

        return config

class EventFilterAndSelectView(discord.ui.View):
    def __init__(
        self,
        status_options,
        selected_status,
        event_options,
        on_status_select,
        on_event_select,
        placeholder_status="Filter by status...",
        placeholder_event="Pick an event...",
    ):
        super().__init__(timeout=120)

        self.status_select = discord.ui.Select(
            placeholder=placeholder_status,
            options=[
                discord.SelectOption(
                    label=status.capitalize(),
                    value=status,
                    default=(status == selected_status)
                ) for status in status_options
            ],
            min_values=1, max_values=1,
        )
        self.status_select.callback = on_status_select
        self.add_item(self.status_select)

        if not event_options:
            event_options = [
                discord.SelectOption(label="No events found", value="none", default=True)
            ]
            disabled = True
        else:
            disabled = False

        self.event_select = discord.ui.Select(
            placeholder=placeholder_event,
            options=event_options,
            min_values=1, max_values=1,
            disabled=disabled
        )
        self.event_select.callback = on_event_select
        self.add_item(self.event_select)
        
class TriggerTypeSelectView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption], on_select):
        super().__init__(timeout=120)
        self.select = discord.ui.Select(
            placeholder="Choose a trigger type...",
            options=options,
            min_values=1, max_values=1
        )
        self.select.callback = on_select
        self.add_item(self.select)