import discord
from discord import Embed
from bot.utils.time_parse_paginate import format_discord_timestamp


# === EVENT INFO BUILDER ===
def build_event_embed(event_data, guild_id=None):
    end_date = event_data["end_date"] or "*Ongoing*"
    status_icons = {
        "draft": "📝 Draft",
        "visible": "🔎 Visible",
        "active": "🎉 Active",
        "archived": "📦 Archived"
    }
    event_status = status_icons.get(event_data["event_status"], event_data["event_status"].capitalize())
    event_type = event_data["event_type"].capitalize()
    role_status = "✅" if event_data["role_discord_id"] else "❌"
    embed_status = "✅" if event_data["embed_message_discord_id"] else "❌"
    coordinator_display = f"<@{event_data['coordinator_discord_id']}>" if event_data["coordinator_discord_id"] else "*None*"
    tag_display = event_data["tags"] if event_data["tags"] else "*None*"
    description = event_data["event_description"] if event_data["event_description"] else "*No description*"
    priority = str(event_data["priority"])

    created_edited = f"By: <@{event_data['created_by']}> at {format_discord_timestamp(event_data['created_at'])}"
    if event_data["modified_by"]:
        created_edited += f"\nLast: <@{event_data['modified_by']}> at {format_discord_timestamp(event_data['modified_at'])}"

    embed = Embed(title=f"📋 Event Details: {event_data['event_name']}", color=0x7289DA)
    embed.add_field(name="🆔 Shortcode", value=event_data["event_key"], inline=False)  
    embed.add_field(name="📅 Dates", value=f"Start: {event_data['start_date']}\nEnd: {end_date}", inline=True)
    embed.add_field(name="📌 Status", value=event_status, inline=True)
    embed.add_field(name="🎉 Type", value=event_type, inline=True)
    embed.add_field(name="👤 Coordinator", value=coordinator_display, inline=True)       
    embed.add_field(name="🎭 Role", value=role_status, inline=True)
    embed.add_field(name="🧵 Embed?", value=embed_status, inline=True)
    embed.add_field(name="⭐ Priority", value=priority, inline=True)
    embed.add_field(name="🏷️ Tags", value=tag_display, inline=False)
    embed.add_field(name="✏️ Description", value=description, inline=False)

    if event_data["embed_message_discord_id"] and guild_id:
        jump_link = f"https://discord.com/channels/{guild_id}/{event_data['embed_channel_discord_id']}/{event_data['embed_message_discord_id']}"
        embed.add_field(name="🔗 Embed Link", value=f"[Jump to Embed]({jump_link})", inline=False)

    embed.add_field(name="👩‍💻 Created / Edited By", value=created_edited, inline=False)
    return embed


# === DASHBOARD VIEW ===
class EventDashboardView(discord.ui.View):
    def __init__(self, event_data, actions_data, rewards_data, guild_id=None):
        super().__init__(timeout=300)
        self.event_data = event_data
        self.actions_data = actions_data
        self.rewards_data = rewards_data
        self.guild_id = guild_id

        # Pagination state
        self.actions_page = 0
        self.rewards_page = 0
        self.items_per_page = 10

        self.current_view = "event"  # can be "event", "actions", "rewards"
        self.refresh_buttons()

    # === EMBED BUILDERS ===
    def build_actions_embed(self):
        embed = discord.Embed(
            title=f"⚙️ Actions for {self.event_data['event_name']}",
            color=discord.Color.green()
        )
        if not self.actions_data:
            embed.description = "No actions linked."
            return embed

        start = self.actions_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.actions_data[start:end]

        for ae in page_items:
            reward_display = f"🏆 {ae['reward_event_key']}" if ae["reward_event_key"] else "None"
            embed.add_field(
                name=f"**{ae['action_key']}** (`{ae['variant']}`)",
                value=(f"🎯 Points: {ae['points_granted']} | Reward: {reward_display}\n"
                       f"👁 Visible: {'✅' if ae['is_allowed_during_visible'] else '❌'} | "
                       f"🙋 Self-report: {'✅' if ae['is_self_reportable'] else '❌'}\n"
                       f"💬 Help: {ae['input_help_text'] or 'N/A'}"),
                inline=False
            )

        total_pages = max(1, (len(self.actions_data) - 1) // self.items_per_page + 1)
        embed.set_footer(text=f"Page {self.actions_page + 1}/{total_pages} • {len(self.actions_data)} actions total")
        return embed

    def build_rewards_embed(self):
        embed = discord.Embed(
            title=f"🎁 Rewards for {self.event_data['event_name']}",
            color=discord.Color.gold()
        )
        if not self.rewards_data:
            embed.description = "No rewards linked."
            return embed

        start = self.rewards_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.rewards_data[start:end]

        for re in page_items:
            availability_icon = "🛒" if re["availability"] == "inshop" else "🎯"
            embed.add_field(
                name=f"**{re['reward_name']}** (`{re['reward_key']}`)",
                value=(f"{availability_icon} Availability: {re['availability']} | 💰 Price: {re['price']}"),
                inline=False
            )

        total_pages = max(1, (len(self.rewards_data) - 1) // self.items_per_page + 1)
        embed.set_footer(text=f"Page {self.rewards_page + 1}/{total_pages} • {len(self.rewards_data)} rewards total")
        return embed

    # === BUTTON BUILDER ===
    def refresh_buttons(self):
        self.clear_items()

        if self.current_view == "event":
            self._add_button("Actions", discord.ButtonStyle.success, self.show_actions)
            self._add_button("Rewards", discord.ButtonStyle.secondary, self.show_rewards)

        elif self.current_view == "actions":
            self._add_button("Event Info", discord.ButtonStyle.primary, self.show_event)
            if self.actions_page > 0:
                self._add_button("⬅️ Prev", discord.ButtonStyle.secondary, self.prev_actions)
            if (self.actions_page + 1) * self.items_per_page < len(self.actions_data):
                self._add_button("Next ➡️", discord.ButtonStyle.secondary, self.next_actions)
            self._add_button("Rewards", discord.ButtonStyle.secondary, self.show_rewards)

        elif self.current_view == "rewards":
            self._add_button("Event Info", discord.ButtonStyle.primary, self.show_event)
            self._add_button("Actions", discord.ButtonStyle.success, self.show_actions)
            if self.rewards_page > 0:
                self._add_button("⬅️ Prev", discord.ButtonStyle.secondary, self.prev_rewards)
            if (self.rewards_page + 1) * self.items_per_page < len(self.rewards_data):
                self._add_button("Next ➡️", discord.ButtonStyle.secondary, self.next_rewards)

    def _add_button(self, label, style, callback):
        btn = discord.ui.Button(label=label, style=style)
        btn.callback = callback
        self.add_item(btn)

    # === CALLBACKS ===
    async def show_event(self, interaction: discord.Interaction):
        self.current_view = "event"
        self.refresh_buttons()
        await interaction.response.edit_message(embed=build_event_embed(self.event_data, self.guild_id), view=self)

    async def show_actions(self, interaction: discord.Interaction):
        self.current_view = "actions"
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_actions_embed(), view=self)

    async def show_rewards(self, interaction: discord.Interaction):
        self.current_view = "rewards"
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_rewards_embed(), view=self)

    async def prev_actions(self, interaction: discord.Interaction):
        if self.actions_page > 0:
            self.actions_page -= 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_actions_embed(), view=self)

    async def next_actions(self, interaction: discord.Interaction):
        max_page = max(0, (len(self.actions_data) - 1) // self.items_per_page)
        if self.actions_page < max_page:
            self.actions_page += 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_actions_embed(), view=self)

    async def prev_rewards(self, interaction: discord.Interaction):
        if self.rewards_page > 0:
            self.rewards_page -= 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_rewards_embed(), view=self)

    async def next_rewards(self, interaction: discord.Interaction):
        max_page = max(0, (len(self.rewards_data) - 1) // self.items_per_page)
        if self.rewards_page < max_page:
            self.rewards_page += 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_rewards_embed(), view=self)