import discord
from discord import Interaction
from discord.ui import View, Button, Modal, TextInput

# ====== MODAL FOR CUSTOM PRICE ======
class PriceModal(discord.ui.Modal, title="💰 Set Custom Price"):
    price_input = discord.ui.TextInput(
        label="Price (non-negative integer)",
        placeholder="e.g., 150",
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self):
        super().__init__()
        self.price_value = None

    async def on_submit(self, interaction: Interaction):
        try:
            value = int(self.price_input.value.strip())
            if value < 0:
                await interaction.response.send_message("❌ Price must be non-negative.", ephemeral=True)
                return
            self.price_value = value
            await interaction.response.defer()
        except ValueError:
            await interaction.response.send_message("❌ Invalid number for price.", ephemeral=True)


# ====== MODAL FOR CUSTOM VARIANT ======
class CustomVariantModal(discord.ui.Modal, title="Custom Variant"):
    variant_input = discord.ui.TextInput(
        label="Enter custom variant",
        placeholder="e.g., seasonal2025",
        required=True
    )

    def __init__(self):
        super().__init__()
        self.variant_value = None

    async def on_submit(self, interaction: Interaction):
        self.variant_value = self.variant_input.value.strip()
        await interaction.response.defer()


# ====== MODAL FOR HELP TEXT ======
class HelpTextModal(discord.ui.Modal, title="User Help Text"):
    help_input = discord.ui.TextInput(
        label="Help text",
        placeholder="Enter instructions for users...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self):
        super().__init__()
        self.help_text = None

    async def on_submit(self, interaction: Interaction):
        self.help_text = self.help_input.value.strip()
        await interaction.response.defer()


# ====== PRICE PICKER VIEW ======
class PricePicker(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)
        self.selected_price = None

    @discord.ui.button(label="0", style=discord.ButtonStyle.secondary)
    async def price_0(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_price = 0
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def price_50(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_price = 50
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def price_100(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_price = 100
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="200", style=discord.ButtonStyle.secondary)
    async def price_200(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_price = 200
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Custom", style=discord.ButtonStyle.primary)
    async def custom_price(self, interaction: Interaction, button: discord.ui.Button):
        modal = PriceModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.price_value is not None:
            self.selected_price = modal.price_value
        self.stop()


# ====== CUSTOM VARIANT BUTTON VIEW ======
class CustomVariantButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)
        self.variant = None

    @discord.ui.button(label="✏️ Enter Custom Variant", style=discord.ButtonStyle.primary)
    async def custom_variant_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomVariantModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.variant_value is not None:
            self.variant = modal.variant_value
        self.stop()


# ====== LAUNCH MODAL BUTTON VIEW ======
class VariantPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)
        self.selected_variant = None

    @discord.ui.button(label="Default", style=discord.ButtonStyle.secondary)
    async def variant_default(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_variant = "default"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Current", style=discord.ButtonStyle.secondary)
    async def variant_current(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_variant = "current"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def variant_previous(self, interaction: Interaction, button: discord.ui.Button):
        self.selected_variant = "previous"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Custom", style=discord.ButtonStyle.primary)
    async def variant_custom(self, interaction: Interaction, button: discord.ui.Button):
        modal = CustomVariantModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.variant_value:
            self.selected_variant = modal.variant_value
        self.stop()


# ====== FORCE CONFIRM VIEW ======
class ForceConfirmView(discord.ui.View):
    def __init__(self, prompt: str):
        super().__init__(timeout=10)
        self.prompt = prompt
        self.confirmed = False

    @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.danger)
    async def yes(self, interaction: Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


# ====== YES/NO VIEW ======
class YesNoView(discord.ui.View):
    def __init__(self, prompt: str):
        super().__init__(timeout=10)
        self.prompt = prompt
        self.confirmed = None

    @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


# ====== HELP TEXT PICKER VIEW ======
class HelpTextPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)
        self.help_text = None

    @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: discord.ui.Button):
        modal = HelpTextModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.help_text:
            self.help_text = modal.help_text
        self.stop()

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: Interaction, button: discord.ui.Button):
        self.help_text = False
        await interaction.response.defer()
        self.stop()


# ====== TOGGLE YES/NO VIEW ======
class ToggleYesNoView(discord.ui.View):
    def __init__(self, prompt: str):
        super().__init__(timeout=10)
        self.prompt = prompt
        self.value = None

    @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


# ====== DROPDOWNS ======
class EventSelect(discord.ui.Select):
    def __init__(self, events):
        options = [
            discord.SelectOption(label=ev.event_name, description=ev.event_key, value=ev.event_key)
            for ev in events
        ]
        super().__init__(placeholder="Select an event…", options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_event_key = self.values[0]
        await interaction.response.defer()
        self.view.stop()


class RewardSelect(discord.ui.Select):
    def __init__(self, rewards):
        options = [
            discord.SelectOption(label=f"{rw.reward_name} ({rw.reward_type})",  value=rw.reward_key)
            for rw in rewards
        ]
        super().__init__(placeholder="Select a reward…", options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_reward_key = self.values[0]
        await interaction.response.defer()
        self.view.stop()


class AvailabilitySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="In shop", value="inshop"),
            discord.SelectOption(label="On action", value="onaction")
        ]
        super().__init__(placeholder="Select availability…", options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_availability = self.values[0]
        await interaction.response.defer()
        self.view.stop()


class RewardEventSelect(discord.ui.Select):
    def __init__(self, reward_events):
        options = [
            discord.SelectOption(
                label=f"{re.reward.reward_name} – {re.availability} – {re.price} pts",
                value=re.reward_event_key
            )
            for re in reward_events
        ]
        super().__init__(placeholder="Select a reward-event…", options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_reward_event_key = self.values[0]
        await interaction.response.defer()
        self.view.stop()


class ActionEventSelect(discord.ui.Select):
    def __init__(self, action_events):
        options = [
            discord.SelectOption(
                label=f"{ae.action.action_key} – {ae.variant}",
                value=ae.action_event_key
            )
            for ae in action_events
        ]
        super().__init__(placeholder="Select a action-event…", options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_action_event_key = self.values[0]
        await interaction.response.defer()
        self.view.stop()


class ActionSelect(discord.ui.Select):
    def __init__(self, actions):
        options = [
            discord.SelectOption(
                label=ac.action_key,                 # main label is the key
                description=ac.action_description[:100],  # short description as hint
                value=ac.action_key                  # value is also the key
            ) for ac in actions
        ]
        super().__init__(placeholder="Select an action…", options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_action_key = self.values[0]
        await interaction.response.defer()
        self.view.stop()


class ActionSelectView(discord.ui.View):
    def __init__(self, actions, timeout=10):
        super().__init__(timeout=timeout)
        self.selected_action_key = None
        self.add_item(ActionSelect(actions))



class PointPickerView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.selected_points = None
        self.custom_points = None
        self.cancelled = False

    @discord.ui.button(label="10", style=discord.ButtonStyle.secondary)
    async def ten(self, interaction: Interaction, button: Button):
        self.selected_points = 10
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="20", style=discord.ButtonStyle.secondary)
    async def twenty(self, interaction: Interaction, button: Button):
        self.selected_points = 20
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def fifty(self, interaction: Interaction, button: Button):
        self.selected_points = 50
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Custom", style=discord.ButtonStyle.primary)
    async def custom(self, interaction: Interaction, button: Button):
        modal = CustomPointsModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.custom_points is not None:
            self.custom_points = modal.custom_points
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, button: Button):
        self.cancelled = True
        self.stop()


class CustomPointsModal(Modal, title="Custom Points"):
    def __init__(self):
        super().__init__(timeout=60)
        self.custom_points = None

        self.points_input = TextInput(
            label="Enter custom point amount (numeric)",
            placeholder="E.g. 35",
            required=True,
            max_length=4
        )
        self.add_item(self.points_input)

    async def on_submit(self, interaction: Interaction):
        try:
            value = int(self.points_input.value)
            if value < 0:
                raise ValueError
            self.custom_points = value
            await interaction.response.defer()
        except ValueError:
            await interaction.response.send_message("❌ Invalid number. Please enter a positive integer.", ephemeral=True)
        finally:
            self.stop()



class SingleSelectView(discord.ui.View):
    def __init__(self, select_component, timeout=10):
        super().__init__(timeout=timeout)
        self.add_item(select_component)
        self.selected_event_key = None
        self.selected_reward_key = None
        self.selected_availability = None
        self.selected_reward_event_key = None
        self.selected_action_key = None
        self.selected_action_event_key = None