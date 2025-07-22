import discord
from discord import app_commands
from discord.ui import View, Button, Select
from discord import ButtonStyle
from typing import Literal
from datetime import datetime
from discord.ext import commands
from discord import Embed, Interaction, SelectOption
import json
import os
import uuid
import utils
from utils import is_admin_or_mod, create_embed_paginator


# ADMIN ONLY COMMANDS
class AdminGroup(app_commands.Group):

    def __init__(self):
        super().__init__(name="admin", description="Admin-only commands")

    # /givepoints
    @app_commands.command(name="givepoints",
                          description="Give points to a user (admin/mod only)")
    @app_commands.describe(user="The member", amount="Number of points")
    async def givepoints(self, interaction: discord.Interaction,
                         user: discord.Member, amount: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True)
            return

        user_data = utils.get_user_data(user.id)
        user_data["points"] += amount
        utils.update_user_data(user.id, user_data)

        await interaction.response.send_message(
            f"Gave {amount} points to {user.display_name}.")

    # /removepoints
    @app_commands.command(
        name="removepoints",
        description="Remove points from a user (admin/mod only)")
    @app_commands.describe(user="The member",
                           amount="Number of points to remove")
    async def removepoints(self, interaction: discord.Interaction,
                           user: discord.Member, amount: int):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True)
            return

        user_data = utils.get_user_data(user.id)
        user_data["points"] = max(0, user_data["points"] -
                                  amount)  # Prevent negative points
        utils.update_user_data(user.id, user_data)

        await interaction.response.send_message(
            f"Removed {amount} points from {user.display_name}.")

    # /addreward
    @app_commands.command(name="addreward", description="Create a new reward.")
    @app_commands.describe(
        reward_type="Type of reward (badge, title, or item)",
        name="Name of the reward",
        description="Short description",
        price="Price in points",
        emoji="Emoji (for badges only)",
        media_url="Image URL (for items only)",
        stackable="Whether the item can be stacked (for items only)")
    async def addreward(self,
                        interaction: discord.Interaction,
                        reward_type: Literal["badge", "title", "item"],
                        name: str,
                        description: str,
                        price: int,
                        emoji: str = None,
                        media_url: str = None,
                        stackable: bool = False):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True)
            return

        warehouse = utils.get_warehouse()
        new_id = utils.generate_next_reward_id(reward_type, warehouse)

        reward = {
            "id": new_id,
            "type": reward_type,
            "name": name,
            "description": description,
            "price": price,
            "times_bought": 0,
            "stackable":
            stackable if reward_type == "item" else False,  # only for items"
            "created_by": interaction.user.id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_by": None,
            "updated_at": None
        }

        if reward_type == "badge":
            if not emoji:
                await interaction.response.send_message(
                    "You must provide an emoji for a badge.", ephemeral=True)
                return
            reward["emoji"] = emoji

        elif reward_type == "item":
            if not media_url:
                await interaction.response.send_message(
                    "You must provide an image URL for an item.",
                    ephemeral=True)
                return
            reward["media_url"] = media_url

        elif reward_type == "item":
            if not stackable:
                await interaction.response.send_message(
                    "You must specify if an item is stackable", ephemeral=True)
                return
            reward["stackable"] = stackable

        warehouse.append(reward)
        utils.save_warehouse(warehouse)

        await interaction.response.send_message(
            f"✅ Reward `{new_id}` added successfully.", ephemeral=True)

    # /listwarehouse
    @app_commands.command(
        name="listwarehouse",
        description="List all rewards in the warehouse (paginated)")
    async def listwarehouse(self, interaction: discord.Interaction):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True)
            return

        warehouse = utils.get_warehouse()
        events = utils.get_events()

        if not warehouse:
            await interaction.response.send_message(
                "📦 The reward warehouse is currently empty.")
            return

        reward_event_map = {}
        for event in events:
            for reward_id in event.get("rewards", []):
                reward_event_map.setdefault(reward_id, []).append(event["event_id"])

        paginator = utils.RewardPaginator(warehouse,
                                          reward_event_map,
                                          user=interaction.user)
        embed = paginator.format_page()
        await interaction.response.send_message(embed=embed, view=paginator)

    # /editreward
    @app_commands.command(name="editreward",
                          description="Edit an existing reward's properties.")
    @app_commands.describe(reward_id="ID of the reward to edit",
                           name="New name (optional)",
                           description="New description (optional)",
                           price="New price (optional)",
                           emoji="New emoji (for badges only)",
                           media_url="New media URL (for items only)",
                           stackable="Change stackability (for items only)")
    async def editreward(self,
                         interaction: discord.Interaction,
                         reward_id: str,
                         name: str = None,
                         description: str = None,
                         price: int = None,
                         emoji: str = None,
                         media_url: str = None,
                         stackable: bool = False):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True)
            return

        warehouse = utils.get_warehouse()
        reward = next(
            (r for r in warehouse if r["id"].upper() == reward_id.upper()),
            None)
        if not reward:
            await interaction.response.send_message("❌ Reward not found.",
                                                    ephemeral=True)
            return

        changes = []
        if name:
            reward["name"] = name
            changes.append("name")
        if description:
            reward["description"] = description
            changes.append("description")
        if price is not None:
            reward["price"] = price
            changes.append("price")
        if emoji and reward["type"] == "badge":
            reward["emoji"] = emoji
            changes.append("emoji")
        if media_url and reward["type"] == "item":
            reward["media_url"] = media_url
            changes.append("media_url")
        if stackable and reward["type"] == "item":
            reward["stackable"] = stackable
            changes.append("stackable")

        if not changes:
            await interaction.response.send_message(
                "⚠️ No valid fields provided to update.", ephemeral=True)
            return

        reward["updated_by"] = interaction.user.id
        reward["updated_at"] = datetime.utcnow().isoformat()
        utils.save_warehouse(warehouse)

        await interaction.response.send_message(
            f"✅ Updated reward `{reward_id}`. Fields changed: {', '.join(changes)}",
            ephemeral=True)

    # /removereward
    @app_commands.command(name="removereward",
                          description="Permanently delete a reward.")
    @app_commands.describe(reward_id="ID of the reward to delete",
                           reason="Optional reason for the deletion")
    async def removereward(self,
                           interaction: discord.Interaction,
                           reward_id: str,
                           reason: str = "No reason provided."):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True)
            return

        reward_id = reward_id.upper()
        warehouse = utils.get_warehouse()
        reward = next((r for r in warehouse if r["id"] == reward_id), None)
        if not reward:
            await interaction.response.send_message("❌ Reward not found.",
                                                    ephemeral=True)
            return

        # Confirmation View
        class ConfirmDelete(View):

            def __init__(self):
                super().__init__(timeout=30)
                self.value = None

            @discord.ui.button(label="✅ Confirm", style=ButtonStyle.danger)
            async def confirm(self, interaction2: discord.Interaction,
                              button: Button):
                if interaction2.user.id != interaction.user.id:
                    await interaction2.response.send_message(
                        "This confirmation isn't for you.", ephemeral=True)
                    return
                self.value = True
                await interaction2.response.defer()
                self.stop()

            @discord.ui.button(label="❌ Cancel", style=ButtonStyle.secondary)
            async def cancel(self, interaction2: discord.Interaction,
                             button: Button):
                if interaction2.user.id != interaction.user.id:
                    await interaction2.response.send_message(
                        "This confirmation isn't for you.", ephemeral=True)
                    return
                self.value = False
                await interaction2.response.defer()
                self.stop()

        view = ConfirmDelete()
        await interaction.response.send_message(
            f"⚠️ Are you **sure** you want to delete reward `{reward_id}` (`{reward['name']}`)?\n"
            f"This will remove it from all users.\n\n"
            f"📝 **Reason:** *{reason}*",
            view=view,
            ephemeral=True)
        await view.wait()

        if view.value is None:
            await interaction.followup.send("⏳ Timed out. Reward not deleted.",
                                            ephemeral=True)
            return
        if not view.value:
            await interaction.followup.send("❌ Deletion cancelled.",
                                            ephemeral=True)
            return

        # Proceed with deletion
        warehouse = [r for r in warehouse if r["id"] != reward_id]
        utils.save_warehouse(warehouse)

        users = utils.get_all_users()
        for uid, data in users.items():
            modified = False

            if reward["type"] == "title":
                if reward_id in data.get("titles", []):
                    data["titles"].remove(reward_id)
                    modified = True
                if data.get("equipped_title") == reward_id:
                    data["equipped_title"] = None
                    modified = True

            elif reward["type"] == "badge":
                if reward_id in data.get("badges", []):
                    data["badges"].remove(reward_id)
                    modified = True

            elif reward["type"] == "item":
                if reward_id in data.get("items", []):
                    data["items"] = [
                        i for i in data["items"] if i != reward_id
                    ]
                    modified = True

            if modified:
                users[uid] = data

        utils.save_all_users(users)
        
        # Unlink reward from any events
        events = utils.get_events()
        updated = False

        for event in events:
            rewards = event.get("rewards", [])
            if reward_id in rewards:
                rewards.remove(reward_id)
                event["rewards"] = rewards
                updated = True

        if updated:
            utils.save_events(events)
        
        # Log deletion
        log_entry = {
            "id": reward_id,
            "type": reward["type"],
            "deleted_by": interaction.user.id,
            "deleted_at": datetime.utcnow().isoformat(),
            "reason": reason
        }
        try:
            if os.path.exists("deletion_log.json"):
                with open("deletion_log.json", "r") as f:
                    try:
                        logs = json.load(f)
                        if not isinstance(logs, list):
                            logs = []
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []

            logs.append(log_entry)
            with open("deletion_log.json", "w") as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Reward deleted, but failed to log the deletion. Error: `{e}`",
                ephemeral=False)
            return

        await interaction.followup.send(
            f"🗑️ Reward `{reward_id}` deleted and logged with reason: *{reason}*",
            ephemeral=False)

    # /givereward
    @app_commands.command(
        name="givereward",
        description="Give a reward manually to a user (admin/mod only).")
    @app_commands.describe(
        member="The user who will receive the reward",
        reward_id="The reward ID to give (case-insensitive)",
        reason="Optional reason for the grant",
        amount="How many to give (only for stackable items)")
    async def givereward(self,
                         interaction: discord.Interaction,
                         member: discord.Member,
                         reward_id: str,
                         reason: str = "No reason provided",
                         amount: int = 1):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True)
            return

        reward_id = reward_id.upper()
        warehouse = utils.get_warehouse()
        reward = next((r for r in warehouse if r["id"] == reward_id), None)

        if not reward:
            await interaction.response.send_message(
                f"❌ Reward ID `{reward_id}` not found.", ephemeral=True)
            return

        user_data = utils.get_user_data(member)
        reward_type = reward["type"]
        updated = False

        if reward_type == "title":
            if reward_id not in user_data["titles"]:
                user_data["titles"].append(reward_id)
                updated = True

        elif reward_type == "badge":
            if reward_id not in user_data["badges"]:
                user_data["badges"].append(reward_id)
                updated = True

        elif reward_type == "item":
            if reward.get("stackable", False):
                for _ in range(amount):
                    user_data["items"].append(reward_id)  # allow duplicates
                updated = True
            elif reward_id not in user_data["items"]:
                user_data["items"].append(reward_id)
                updated = True

        if updated:
            utils.update_user_data(str(member.id), user_data)

            # Determine how many were actually granted
            granted_amount = 0
            if reward_type in ["title", "badge"]:
                if updated:
                    granted_amount = 1
            elif reward_type == "item":
                if reward.get("stackable", False):
                    granted_amount = amount if updated else 0
                else:
                    granted_amount = 1 if updated else 0

            # Increment bought count
            reward["times_bought"] = reward.get("times_bought",
                                                0) + granted_amount
            for i, r in enumerate(warehouse):
                if r["id"] == reward_id:
                    warehouse[i] = reward
                    break
            utils.save_warehouse(warehouse)

            # Log
            utils.log_reward_action(user_id=member.id,
                                    reward_id=reward["id"],
                                    reward_type=reward["type"],
                                    action="granted",
                                    amount=granted_amount,
                                    reason=reason,
                                    performed_by=interaction.user.id)

            # Response message
            if reward.get("stackable", False):
                msg = f"✅ Gave reward **{reward['name']}** ×{amount} (`{reward_id}`) to {member.mention}."
            else:
                msg = f"✅ Gave reward **{reward['name']}** (`{reward_id}`) to {member.mention}."

            await interaction.response.send_message(msg, ephemeral=False)

        else:
            await interaction.response.send_message(
                f"⚠️ {member.mention} already has reward `{reward_id}`.",
                ephemeral=True)

    # /takereward
    @app_commands.command(name="takereward",
                          description="Remove a reward from a user.")
    @app_commands.describe(
        member="The user to remove the reward from",
        reward_id="The reward ID to remove",
        reason="Optional reason for the removal",
        amount="How many to remove (only for stackable items)",
        remove_all="Remove all instances (only for stackable items)")
    async def takereward(self,
                         interaction: discord.Interaction,
                         member: discord.Member,
                         reward_id: str,
                         reason: str = "No reason provided",
                         amount: int = 1,
                         remove_all: bool = False):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True)
            return

        reward_id = reward_id.upper()
        warehouse = utils.get_warehouse()
        reward = next((r for r in warehouse if r["id"] == reward_id), None)

        if not reward:
            await interaction.response.send_message(
                f"❌ Reward `{reward_id}` not found.", ephemeral=True)
            return

        user_data = utils.get_user_data(member)

        reward_type = reward["type"]
        updated = False
        success = False

        if reward_type == "title":
            if reward_id in user_data["titles"]:
                user_data["titles"].remove(reward_id)

                if user_data.get("equipped_title") == reward_id:
                    user_data["equipped_title"] = None
                updated = True
                success = True

        elif reward_type == "badge":
            if reward_id in user_data["badges"]:
                user_data["badges"].remove(reward_id)
                updated = True
                success = True

        elif reward_type == "item":
            if reward.get("stackable", False):
                current_items = user_data.get("items", [])
                count = current_items.count(reward_id)

                if remove_all:
                    if count > 0:
                        user_data["items"] = [
                            i for i in current_items if i != reward_id
                        ]
                        updated = True
                        success = True
                else:
                    if count >= amount:
                        removed = 0
                        new_items = []
                        for item in current_items:
                            if item == reward_id and removed < amount:
                                removed += 1
                                continue
                            new_items.append(item)
                        user_data["items"] = new_items
                        updated = True
                        success = removed > 0
            else:
                if reward_id in user_data["items"]:
                    user_data["items"].remove(reward_id)
                    updated = True
                    success = True

        if updated:
            utils.update_user_data(member.id, user_data)
            # Normalize amount for non-stackable rewards
            log_amount = amount if reward_type == "item" and reward.get(
                "stackable", False) else 1

            # Log
            utils.log_reward_action(user_id=member.id,
                                    reward_id=reward["id"],
                                    reward_type=reward["type"],
                                    action="removed",
                                    amount=log_amount,
                                    reason=reason,
                                    performed_by=interaction.user.id)
            await interaction.response.send_message(
                f"🗑️ Removed `{reward_id}` from {member.mention} successfully.",
                ephemeral=False)
        else:
            await interaction.response.send_message(
                f"⚠️ {member.mention} does not have the reward `{reward_id}` or insufficient quantity.",
                ephemeral=True)

    # /rewardhistory
    @app_commands.command(
        name="rewardhistory",
        description="View reward transaction history for a user.")
    @app_commands.describe(
        member="User to view reward history for",
        reward_type="Filter by type: badge, title or item",
        performed_by="Filter actions done by a specific admin/mod")
    async def rewardhistory(self,
                            interaction: discord.Interaction,
                            member: discord.Member = None,
                            reward_type: str = None,
                            performed_by: discord.Member = None):

        if not is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True)
            return

        if not os.path.exists("reward_log.json"):
            await interaction.response.send_message("No reward history found.",
                                                    ephemeral=True)
            return

        try:
            with open("reward_log.json", "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            await interaction.response.send_message(
                "❌ Failed to read reward history log.", ephemeral=True)
            return

        user_id = str(member.id) if member else None

        filtered = [
            log for log in logs
            if (user_id is None or str(log.get("user_id")) == user_id) and (
                reward_type is None or log.get("reward_type") == reward_type)
            and (performed_by is None
                 or str(log.get("performed_by")) == str(performed_by.id))
        ]

        if not filtered:
            await interaction.response.send_message(
                "No matching reward history found.", ephemeral=True)
            return

        # Load warehouse to resolve reward names
        warehouse = utils.get_warehouse()
        warehouse_map = {r["id"]: r["name"] for r in warehouse}

        # Format entries
        pages = []
        PAGE_SIZE = 5
        for i in range(0, len(filtered), PAGE_SIZE):
            chunk = filtered[i:i + PAGE_SIZE]
            embed = discord.Embed(title="📜 Reward History",
                                  color=discord.Color.teal())

            for entry in chunk:
                action = entry.get("action", "unknown").capitalize()
                timestamp = entry.get("timestamp", "N/A")
                try:
                    timestamp = datetime.fromisoformat(timestamp).strftime(
                        "%Y-%m-%d %H:%M")
                except Exception:
                    pass

                reward_id = entry.get("reward_id", "❓")
                reward_name = warehouse_map.get(reward_id, "❌ Deleted Reward")
                reward_type_disp = entry.get("reward_type", "unknown")

                user_line = f"<@{entry['user_id']}> (`{entry['user_id']}`)"
                mod_line = f"<@{entry['performed_by']}> (`{entry['performed_by']}`)"
                reason_line = entry.get("reason", "No reason provided.")

                amount = entry.get("amount")
                amount_text = "all" if entry.get("remove_all") else (
                    f"x{amount}" if amount else "1")

                embed.add_field(
                    name=f"{action} • {timestamp}",
                    value=(
                        f"👤 User: {user_line}\n"
                        f"🏅 Reward: **{reward_name}** (`{reward_type_disp} - {reward_id}`)\n"
                        f"📦 Quantity: {amount_text}\n"
                        f"🔧 By: {mod_line}\n"
                        f"📝 Reason: *{reason_line}*"),
                    inline=False)

            embed.set_footer(text="David's Workshop")
            pages.append(embed)

        await interaction.response.send_message(
            embed=pages[0], view=utils.create_embed_paginator(pages))

    # /rewardinfo
    @app_commands.command(
        name="rewardinfo",
        description="View detailed information about a reward (admin only).")
    @app_commands.describe(reward_id="The ID of the reward to inspect")
    async def rewardinfo(self, interaction: Interaction, reward_id: str):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True)
            return

        reward_id = reward_id.upper()
        warehouse = utils.get_warehouse()
        reward = next((r for r in warehouse if r["id"] == reward_id), None)

        if not reward:
            await interaction.response.send_message(
                f"❌ Reward `{reward_id}` not found.", ephemeral=True)
            return

        # Load events and reverse map (reward_id -> [event names])
        event_links = utils.get_events()
        reward_events = []
        for event in event_links:
            if reward_id in event.get("rewards", []):
                reward_events.append(event.get("name", "Unnamed Event"))

        embed = Embed(title=f"Reward Info\n{reward.get('name', 'Unnamed')}",
                      color=0x7289DA)
        embed.add_field(name="🆔 ID", value=reward.get("id"), inline=True)
        embed.add_field(name="📂 Type",
                        value=reward.get("type").capitalize(),
                        inline=True)

        if reward.get("description"):
            embed.add_field(name="📝 Description",
                            value=reward["description"],
                            inline=False)

        if reward["type"] == "badge":
            embed.add_field(name="🏅 Emoji",
                            value=reward.get("emoji", "❔"),
                            inline=True)
        elif reward["type"] == "item":
            media_url = reward.get("media_url")
            if media_url:
                embed.add_field(name="🖼️ Media",
                                value=f"[View Media]({media_url})",
                                inline=True)
                embed.add_field(name="📦 Stackable",
                    value="✅ Yes" if reward.get(
                    "stackable", False) else "❌ No",
                    inline=True)

        embed.add_field(name=" ",
            value="\n",
            inline=False)
        
        embed.add_field(name="💵 Price",
                        value=reward.get("price", "N/A"),
                        inline=True)
        embed.add_field(name="📈 Times Bought",
                        value=reward.get("times_bought", 0),
                        inline=True)

        if reward_events:
            embed.add_field(name="📎 Linked Events",
                            value=", ".join(reward_events),
                            inline=False)
        else:
            embed.add_field(name="📎 Linked Events", value="None", inline=True)

        # Metadata: creation & updates
        created_by = reward.get("created_by")
        created_at = reward.get("created_at")
        updated_by = reward.get("updated_by")
        updated_at = reward.get("updated_at")

        def format_user(uid):
            return f"<@{uid}>" if uid else "N/A"

        def format_time(ts):
            try:
                return f"<t:{int(datetime.fromisoformat(ts).timestamp())}:f>"
            except Exception:
                return ts or "N/A"

        meta_lines = []
        if created_by or created_at:
            meta_lines.append(
                f"🛠️ Created by {format_user(created_by)} on {format_time(created_at)}"
            )
        if updated_by or updated_at:
            meta_lines.append(
                f"🔁 Last updated by {format_user(updated_by)} on {format_time(updated_at)}"
            )

        if meta_lines:
            embed.add_field(name="📅 Metadata",
                            value="\n".join(meta_lines),
                            inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /createevent
    @app_commands.command(name="createevent", description="Create a new event (admin only).")
    @app_commands.describe(
        code="Short code for the event (used in ID)",
        name="Display name of the event",
        description="A brief description of the event",
        start_date="Start date (YYYY-MM-DD)",
        end_date="End date (YYYY-MM-DD)",
        coordinator="User coordinating the event (optional)",
        rules_url="Link to the rules post (optional)",
        signup_url="Link to the signup form (optional)",
        banner_url="Optional banner image",
        playlist_url="Optional playlist link",
        shop_section_id="Optional shop section to link",
        priority="Priority order (lower shows first)",
        color="Embed color in hex (e.g. #7289DA)",
        tags="Comma-separated tags (e.g. rp, halloween, big-event)"
    )
    async def createevent(
        self,
        interaction: discord.Interaction,
        code: str,
        name: str,
        description: str,
        start_date: str,
        end_date: str,
        coordinator: discord.Member = None,
        rules_url: str = None,
        signup_url: str = None,
        banner_url: str = None,
        playlist_url: str = None,
        shop_section_id: str = None,
        priority: int = 0,
        color: str = "#7289DA",
        tags: str = None
    ):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        # Parse and validate date
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format. Use `YYYY-MM-DD`.", ephemeral=True)
            return

        # Parse hex color
        try:
            embed_color = int(color.lstrip("#"), 16)
        except ValueError:
            await interaction.response.send_message("❌ Invalid color format. Use `#RRGGBB` hex format.", ephemeral=True)
            return

        # Parse tags
        tag_list = [tag.strip().lower() for tag in tags.split(",")] if tags else []

        try:
            event = utils.create_event(
                code=code,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                created_by=interaction.user.id,
                coordinator_id=coordinator.id if coordinator else None,
                rules_url=rules_url,
                signup_url=signup_url,
                banner_url=banner_url,
                playlist_url=playlist_url,
                shop_section_id=shop_section_id,
                priority=priority,
                embed_color=embed_color,
                tags=tag_list,
                custom_links={}
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: `{e}`", ephemeral=True)
            return

        utils.log_event_action(
            event_id=event["event_id"],
            action_type="created",
            performed_by=interaction.user.id,
            reason=None
        )
        
        await interaction.response.send_message(
            f"✅ Event `{event['name']}` (`{event['event_id']}`) created successfully.",
            ephemeral=False
        )


    
    # /eventlog
    @app_commands.command(name="eventlog", description="View the event log (admin only).")
    @app_commands.describe(performed_by="Filter actions done by a specific admin/mod")
    async def eventlog(self, 
                       interaction: discord.Interaction, performed_by: discord.Member = None):
        if not is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True)
            return
        if not os.path.exists("event_log.json"):
            await interaction.response.send_message("No event log found.",
                                                    ephemeral=True)
            return
    
        try:
            with open("event_log.json", "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            await interaction.response.send_message(
                "❌ Failed to read event log.", ephemeral=True)
            return
    
        filtered = [
            log for log in logs
            if (performed_by is None
                 or str(log.get("performed_by")) == str(performed_by.id))
        ]
    
        if not filtered:
            await interaction.response.send_message(
                "No matching event log found.", ephemeral=True)
            return			
        # Load events to resolve event names
        events = utils.get_events()
        event_map = {e["event_id"]: e.get("name", "Unnamed Event") for e in events}
    
        # Format entries into embeds
        pages = []
        PAGE_SIZE = 5
        for i in range(0, len(filtered), PAGE_SIZE):
            chunk = filtered[i:i + PAGE_SIZE]
            embed = discord.Embed(
                title="📜 Event History",
                color=discord.Color.teal()
            )
    
            for entry in chunk:
                action = entry.get("action", "unknown").capitalize()
                timestamp = entry.get("timestamp", "N/A")
                try:
                    timestamp = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
    
                event_id = entry.get("event_id", "❓")
                event_name = event_map.get(event_id, "❌ Deleted or Unknown Event")
                mod_line = f"<@{entry['performed_by']}> (`{entry['performed_by']}`)"
                reason_line = entry.get("reason", "No reason provided.")
    
                embed.add_field(
                    name=f"{action} • {timestamp}",
                    value=(
                        f"📛 **{event_name} (`{event_id}`)\n"
                        f"👤 **By:** {mod_line}\n"
                        f"📝 Reason: *{reason_line}*"),
                    inline=False)
    
            embed.set_footer(text="David's Workshop")
            pages.append(embed)
    
        await interaction.response.send_message(
        embed=pages[0], view=utils.create_embed_paginator(pages))

    # /editevent
    @app_commands.command(name="editevent", description="Edit an existing event (admin only).")
    @app_commands.describe(
        event_id="ID or code of the event to edit",
        name="New name (optional)",
        description="New description (optional)",
        start_date="New start date (YYYY-MM-DD, optional)",
        end_date="New end date (YYYY-MM-DD, optional)",
        coordinator="New coordinator (optional)",
        rules_url="New rules post link (optional)",
        signup_url="New signup form link (optional)",
        banner_url="New banner image (optional)",
        playlist_url="New playlist link (optional)",
        shop_section_id="New shop section (optional)",
        priority="New priority (lower shows first)",
        color="New embed color in hex (#7289DA)",
        tags="Comma-separated new tags (optional)",
        reason="Reason for the edit (logged)"
    )
    async def editevent(
        self,
        interaction: discord.Interaction,
        event_id: str,
        name: str = None,
        description: str = None,
        start_date: str = None,
        end_date: str = None,
        coordinator: discord.Member = None,
        rules_url: str = None,
        signup_url: str = None,
        banner_url: str = None,
        playlist_url: str = None,
        shop_section_id: str = None,
        priority: int = None,
        color: str = None,
        tags: str = None,
        reason: str = None
):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return

        event = utils.get_event_by_id(event_id)
        if not event:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True)
            return
    
        changes = {}
    
        def try_update(field, new_value):
            if new_value is not None and str(event.get(field)) != str(new_value):
                changes[field] = {"old": event.get(field), "new": new_value}
                event[field] = new_value
    
        # Validate and apply changes
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                try_update("start_date", start_date)
            except ValueError:
                await interaction.response.send_message("❌ Invalid start date format. Use `YYYY-MM-DD`.", ephemeral=True)
                return
    
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
                try_update("end_date", end_date)
            except ValueError:
                await interaction.response.send_message("❌ Invalid end date format. Use `YYYY-MM-DD`.", ephemeral=True)
                return
    
        if color:
            try:
                embed_color = int(color.lstrip("#"), 16)
                try_update("embed_color", embed_color)
            except ValueError:
                await interaction.response.send_message("❌ Invalid color format. Use hex like `#7289DA`.", ephemeral=True)
                return
    
        if tags:
            tag_list = [tag.strip().lower() for tag in tags.split(",")]
            try_update("tags", tag_list)
    
        # Core metadata
        try_update("name", name)
        try_update("description", description)
        try_update("rules_url", rules_url)
        try_update("signup_url", signup_url)
        try_update("banner_url", banner_url)
        try_update("playlist_url", playlist_url)
        try_update("shop_section_id", shop_section_id)
        try_update("priority", priority)
        try_update("coordinator_id", coordinator.id if coordinator else None)
    
        if not changes:
            await interaction.response.send_message("No changes were made.", ephemeral=True)
            return
    
        # Save the event
        all_events = utils.get_events()
        for i, e in enumerate(all_events):
            if e["event_id"] == event["event_id"]:
                all_events[i] = event
                break
        utils.save_events(all_events)
    
        # Log the edit
        utils.log_event_action(
            action_type="edited",
            event_id=event["event_id"],
            performed_by=interaction.user.id,
            reason=reason,
            details= changes
        )
    
        await interaction.response.send_message(
            f"✅ Event `{event['name']}` (`{event['event_id']}`) updated successfully.",
            ephemeral=False
        )

    # /deleteevent
    @app_commands.command(name="deleteevent", description="Delete an event (admin only).")
    @app_commands.describe(event_id="ID or code of the event to delete", reason="Optional reason for deletion")
    async def deleteevent(self, interaction: discord.Interaction, event_id: str, reason: str = "No reason provided."):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
    
        event = utils.get_event_by_id(event_id)
        if not event:
            await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
            return
    
        class ConfirmDeleteView(View):
            def __init__(self):
                super().__init__(timeout=30)
                self.confirmed = None
    
            @discord.ui.button(label="✅ Confirm", style=ButtonStyle.danger)
            async def confirm(self, interaction2: discord.Interaction, button: Button):
                if interaction2.user.id != interaction.user.id:
                    await interaction2.response.send_message("This confirmation isn’t for you.", ephemeral=True)
                    return
                self.confirmed = True
                await interaction2.response.defer()
                self.stop()
    
            @discord.ui.button(label="❌ Cancel", style=ButtonStyle.secondary)
            async def cancel(self, interaction2: discord.Interaction, button: Button):
                if interaction2.user.id != interaction.user.id:
                    await interaction2.response.send_message("This confirmation isn’t for you.", ephemeral=True)
                    return
                self.confirmed = False
                await interaction2.response.defer()
                self.stop()
    
        view = ConfirmDeleteView()
        await interaction.response.send_message(
            f"⚠️ Are you **sure** you want to delete the event `{event['name']}` (`{event['event_id']}`)? This action is irreversible.",
            view=view,
            ephemeral=True
        )
    
        await view.wait()
    
        if view.confirmed is None:
            await interaction.followup.send("⏳ Timed out. Event not deleted.", ephemeral=True)
            return
        if not view.confirmed:
            await interaction.followup.send("❌ Event deletion cancelled.", ephemeral=True)
            return
    
        # Perform deletion
        events = utils.get_events()
        events = [e for e in events if e["event_id"] != event["event_id"]]
        utils.save_events(events)
    
        # Log deletion
        utils.log_event_action(
            action_type="deleted",
            event_id=event["event_id"],
            performed_by=interaction.user.id,
            reason=reason
        )
    
        await interaction.followup.send(
            f"🗑️ Event `{event['name']}` (`{event['event_id']}`) has been deleted and logged.",
            ephemeral=False
        )





    # /eventlinkreward
    @app_commands.command(name="eventlinkreward", description="Link reward(s) to an event via dropdown.")
    @app_commands.describe(event_id="ID or code of the event")
    async def eventlinkreward(self, interaction: discord.Interaction, event_id: str):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message("You don't have permission.", ephemeral=True)
            return

        event = utils.get_event_by_id(event_id)
        if not event:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True)
            return

        view = utils.RewardLinkSelectView(interaction, event)
        await interaction.response.send_message(f"Select rewards to link to event `{event['name']}`:", view=view, ephemeral=True)
        await view.wait()

        if not view.result:
            await interaction.followup.send("⏳ No selection made or timed out.", ephemeral=True)
            return

        count = 0
        for reward_id in view.result:
            if utils.link_reward_to_event(event["event_id"], reward_id):
                count += 1
                utils.log_event_action(
                    action_type="linked_reward",
                    event_id=event["event_id"],
                    performed_by=interaction.user.id,
                    reason=f"Linked reward `{reward_id}` to event via dropdown."
                )

        await interaction.followup.send(f"✅ Linked `{count}` reward(s) to `{event['name']}`.", ephemeral=True)

    # /eventunlinkreward
    @app_commands.command(name="eventunlinkreward", description="Unlink reward(s) from an event via dropdown.")
    @app_commands.describe(event_id="ID or code of the event")
    async def eventunlinkreward(self, interaction: discord.Interaction, event_id: str):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message("You don't have permission.", ephemeral=True)
            return

        event = utils.get_event_by_id(event_id)
        if not event:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True)
            return

        if not event.get("rewards"):
            await interaction.response.send_message(f"ℹ️ No rewards are currently linked to `{event['name']}`.", ephemeral=True)
            return

        view = utils.RewardUnlinkSelectView(interaction, event)
        if not view.select.options:
            await interaction.response.send_message("❌ No rewards available to unlink.", ephemeral=True)
            return

        await interaction.response.send_message(f"Select reward(s) to unlink from `{event['name']}`:", view=view, ephemeral=True)
        await view.wait()

        if not view.result:
            await interaction.followup.send("⏳ No selection made or timed out.", ephemeral=True)
            return

        count = 0
        for reward_id in view.result:
            if utils.unlink_reward_from_event(event["event_id"], reward_id):
                count += 1
                utils.log_event_action(
                    action_type="unlinked_reward",
                    event_id=event["event_id"],
                    performed_by=interaction.user.id,
                    reason=f"Unlinked reward `{reward_id}` from event via dropdown."
                )

        await interaction.followup.send(f"✅ Unlinked `{count}` reward(s) from `{event['name']}`.", ephemeral=True)


    # /eventmenu - Admin menu with filtering
    @app_commands.command(name="eventmenu", description="View full details of all events (1 per page, with filters)")
    @app_commands.describe(
        name="Filter by event name",
        code="Filter by event code",
        month="Filter by start month (MM-YYYY)",
        tag="Filter by tag",
        created_by="Filter by creator",
        coordinator="Filter by coordinator",
        active="Only show active events",
        visible="Only show visible events"
    )
    async def eventmenu(
        self,
        interaction: discord.Interaction,
        name: str = None,
        code: str = None,
        month: str = None,
        tag: str = None,
        created_by: discord.Member = None,
        coordinator: discord.Member = None,
        active: bool = None,
        visible: bool = None
    ):
        if not utils.is_admin_or_mod(interaction.user):
            await interaction.response.send_message("You don't have permission.", ephemeral=True)
            return
    
        events = utils.get_events()
    
        # Apply filters
        def match(event):
            if name and name.lower() not in event.get("name", "").lower():
                return False
            if code and code.lower() != event.get("code", "").lower():
                return False
            if month:
                try:
                    filter_month = datetime.strptime(month, "%m-%Y")
                    event_start = datetime.strptime(event.get("start_date", "0000-00-00"), "%Y-%m-%d")
                    if event_start.month != filter_month.month or event_start.year != filter_month.year:
                        return False
                except:
                    return False
            if tag and tag.lower() not in [t.lower() for t in event.get("tags", [])]:
                return False
            if created_by and str(event.get("created_by")) != str(created_by.id):
                return False
            if coordinator and str(event.get("coordinator_id")) != str(coordinator.id):
                return False
            if active is not None and event.get("active") != active:
                return False
            if visible is not None and event.get("visible") != visible:
                return False
            return True
    
        filtered = [e for e in events if match(e)]
    
        if not filtered:
            await interaction.response.send_message("No matching events found.", ephemeral=True)
            return
    
        # Build paginated embeds
        pages = []
        warehouse = utils.get_warehouse()
        reward_map = {r["id"]: r["name"] for r in warehouse}
        for i, event in enumerate(filtered):
            embed = discord.Embed(title=f"📆 Event: {event['name']}", color=event.get("embed_color", 0x7289DA))
            embed.add_field(name="🆔 ID", value=event.get("event_id", event.get("id")), inline=True)
            embed.add_field(name="🔤 Code", value=event.get("code"), inline=True)
            embed.add_field(name="📅 Start", value=event.get("start_date"), inline=True)
            embed.add_field(name="📅 End", value=event.get("end_date"), inline=True)
            embed.add_field(name="👤 Coordinator", value=f"<@{event.get('coordinator_id')}>" if event.get("coordinator_id") else "None", inline=True)
            embed.add_field(name="🔧 Created by", value=f"<@{event.get('created_by')}>" if event.get("created_by") else "Unknown", inline=True)
            embed.add_field(name="👁️ Visible", value="✅" if event.get("visible") else "❌", inline=True)
            embed.add_field(name="🔥 Active", value="✅" if event.get("active") else "❌", inline=True)
            embed.add_field(name="🏷️ Tags", value=", ".join(event.get("tags", [])) or "None", inline=False)
    
            # Links
            if event.get("rules_url"):
                embed.add_field(name="📜 Rules", value=f"[View]({event['rules_url']})", inline=True)
            if event.get("signup_url"):
                embed.add_field(name="📝 Signup", value=f"[Form]({event['signup_url']})", inline=True)
            if event.get("banner_url"):
                embed.set_image(url=event['banner_url'])
            if event.get("playlist_url"):
                embed.add_field(name="🎵 Playlist", value=f"[Link]({event['playlist_url']})", inline=True)
    
            # Rewards
            rewards = event.get("rewards", [])
            if rewards:
                reward_lines = []
                for rid in rewards:
                    name = reward_map.get(rid, "❓ Unknown")
                    rtype = next((r['type'] for r in warehouse if r['id'] == rid), '?')
                    reward_lines.append(f"`{rtype}` • {name} (`{rid}`)")
                embed.add_field(name=f"🎁 Rewards ({len(rewards)})", value="\n".join(reward_lines), inline=False)
            else:
                embed.add_field(name="🎁 Rewards", value="None linked", inline=False)
    
            embed.set_footer(text=f"Page {i+1} of {len(filtered)}")
            pages.append(embed)
    
        await interaction.response.send_message(embed=pages[0], view=utils.create_embed_paginator(pages), ephemeral=False)
