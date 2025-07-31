import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from typing import Optional

from bot.crud import rewards_crud
from bot.config import REWARDS_PER_PAGE, LOGS_PER_PAGE, REWARD_PRESET_CHANNEL_ID, REWARD_PRESET_ARCHIVE_CHANNEL_ID
from bot.utils import admin_or_mod_check, confirm_action, paginate_embeds, format_discord_timestamp, format_log_entry, now_unix
from db.database import db_session


class AdminRewardCommands(commands.GroupCog, name="admin_reward"):
    """Admin commands for managing rewards."""

    def __init__(self, bot):
        self.bot = bot

    # === HELPER: Auto-prefix reward IDs ===
    def ensure_reward_prefix(self, reward_id: str, reward_type: str) -> str:
        """Ensures the reward_id has the correct prefix for its type."""
        prefix_map = {
            "title": "t_",
            "badge": "b_",
            "preset": "p_"
        }
        prefix = prefix_map.get(reward_type.lower())
        if prefix and not reward_id.lower().startswith(prefix):
            return f"{prefix}{reward_id}"
        return reward_id

    # === CREATE REWARD ===
    @admin_or_mod_check()
    @app_commands.describe(
        reward_id="Shortcode for the reward (prefix auto-added: t_, b_, p_ depending on type)",
        reward_type="Type of reward: title, badge, preset",
        reward_name="Display name of the reward",
        description="Optional description for the reward",
        emoji="Optional emoji for badge rewards (required if type=badge)",
        stackable="Whether this reward can stack in inventory (default: False)"
    )
    @app_commands.command(name="create", description="Create a new reward.")
    async def create_reward(
        self,
        interaction: Interaction,
        reward_id: str,
        reward_type: str,
        reward_name: str,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
        stackable: Optional[bool] = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Ensure correct prefix for the type
        reward_id = self.ensure_reward_prefix(reward_id, reward_type)

        # Enforce emoji requirement for badges
        if reward_type.lower() == "badge" and not emoji:
            await interaction.followup.send("❌ Badge rewards must have an emoji.")
            return

        with db_session() as session:
            if rewards_crud.get_reward(session, reward_id):
                await interaction.followup.send(f"❌ Reward `{reward_id}` already exists.")
                return

            rewards_crud.create_reward(
                session,
                reward_data={
                    "reward_id": reward_id,
                    "reward_type": reward_type.lower(),
                    "reward_name": reward_name,
                    "description": description,
                    "emoji": emoji,
                    "stackable": stackable,
                    "created_by": str(interaction.user.id)
                },
                performed_by=str(interaction.user.id)
            )

        await interaction.followup.send(f"✅ Reward `{reward_name}` created with ID `{reward_id}`.")


    # === EDIT REWARD ===
    @admin_or_mod_check()
    @app_commands.describe(
        reward_id="ID of the reward to edit",
        name="New name for the reward (optional)",
        description="New description for the reward (optional)",
        emoji="New emoji (optional)",
        stackable="Set True/False to change stackability (optional)",
        force="Override restrictions for active events"
    )
    @app_commands.command(name="edit", description="Edit an existing reward.")
    async def edit_reward(
        self,
        interaction: Interaction,
        reward_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
        stackable: Optional[bool] = None,
        force: bool = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward = rewards_crud.get_reward(session, reward_id)
            if not reward:
                await interaction.followup.send(f"❌ Reward `{reward_id}` not found.")
                return

            if rewards_crud.reward_is_linked_to_active_event(session, reward_id):
                blocked_fields = any([
                    name is not None,
                    stackable is not None,
                    emoji is not None
                ])
                if blocked_fields and not force:
                    await interaction.followup.send(
                        "❌ This reward is linked to an **active event**. "
                        "Editing these fields is blocked without `--force`."
                    )
                    return

                if force:
                    confirmed = await confirm_action(
                        interaction,
                        f"reward `{reward_id}` linked to an ACTIVE event",
                        "⚠️ **FORCED OVERRIDE** — this may impact participants!")
                    if not confirmed:
                        return

            updates = {}
            if name:
                updates["reward_name"] = name
            if description is not None:
                updates["description"] = description
            if emoji is not None:
                updates["emoji"] = emoji
            if stackable is not None:
                updates["stackable"] = stackable

            if not updates:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return

            rewards_crud.update_reward(
                session,
                reward_id=reward_id,
                updates=updates,
                performed_by=str(interaction.user.id)
            )

        await interaction.followup.send(f"✅ Reward `{reward_id}` updated successfully.")


    # === DELETE REWARD ===
    @admin_or_mod_check()
    @app_commands.describe(
        reward_id="ID of the reward to delete",
        force="Override restrictions for active events"
    )
    @app_commands.command(name="delete", description="Delete a reward.")
    async def delete_reward(self, interaction: Interaction, reward_id: str,
                           force: bool = False):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward = rewards_crud.get_reward(session, reward_id)
            if not reward:
                await interaction.followup.send(f"❌ Reward `{reward_id}` not found.")
                return

        confirmed = await confirm_action(interaction, f"reward `{reward_id}`", "Removal")
        if not confirmed:
            await interaction.edit_original_response(content="❌ Deletion cancelled or timed out.", view=None)

            if rewards_crud.reward_is_linked_to_active_event(session, reward_id):
                if not force:
                    await interaction.followup.send(
                        "❌ Cannot delete a reward linked to an active event without `--force`."
                    )
                    return
                confirmed = await confirm_action(
                    interaction,
                    f"reward `{reward_id}` linked to an ACTIVE event",
                    "⚠️ **FORCED DELETE** — this will impact participants!"
                    )
                if not confirmed:
                    return

            return

        with db_session() as session:
            rewards_crud.delete_reward(session, reward_id, performed_by=str(interaction.user.id))

        await interaction.edit_original_response(content=f"✅ Reward `{reward_id}` deleted.", view=None)


    # === LIST REWARDS ===
    @admin_or_mod_check()
    @app_commands.describe(
        type="Filter by reward type (title, badge, preset)",
        mod="Filter by moderator who created or last modified",
        name="Search rewards by name (partial match)"
    )
    @app_commands.command(name="list", description="List all rewards with optional filters.")
    async def list_rewards(
        self,
        interaction: Interaction,
        type: Optional[str] = None,
        mod: Optional[discord.User] = None,
        name: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        mod_id = str(mod.id) if mod else None

        with db_session() as session:
            rewards = rewards_crud.get_all_rewards(
                session,
                type=type,
                mod_id=mod_id,
                name=name
            )

            if not rewards:
                await interaction.followup.send("❌ No rewards found with those filters.")
                return

            pages = []
            for i in range(0, len(rewards), REWARDS_PER_PAGE):
                chunk = rewards[i:i+REWARDS_PER_PAGE]
                embed = Embed(title=f"🏆 Rewards List ({i+1}-{i+len(chunk)}/{len(rewards)})")
                for r in chunk:
                    updated_by = f"<@{r.modified_by}>" if r.modified_by else f"<@{r.created_by}>"
                    formatted_time = format_discord_timestamp(r.modified_at or r.created_at)
                    lines = [
                        f"**ID:** `{r.reward_id}` | **Name:** {r.reward_name} | **Type:** {r.reward_type}",
                        f"👤 Last updated by: {updated_by}",
                        f"🕒 On: {formatted_time}",
                    ]
                    embed.add_field(name="\n", value="\n".join(lines), inline=False)
                pages.append(embed)

        await paginate_embeds(interaction, pages)


    # === SHOW REWARD DETAILS ===
    @admin_or_mod_check()
    @app_commands.describe(
        reward_id="ID of the reward to view in detail"
    )
    @app_commands.command(name="show", description="Show full details of a reward.")
    async def show_reward(self, interaction: Interaction, reward_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward = rewards_crud.get_reward(session, reward_id)
            if not reward:
                await interaction.followup.send(f"❌ Reward `{reward_id}` not found.")
                return

            created_edited = f"By: <@{reward.created_by}> at {format_discord_timestamp(reward.created_at)}"
            if reward.modified_by:
                created_edited += f"\nLast: <@{reward.modified_by}> at {format_discord_timestamp(reward.modified_at)}"

            embed = Embed(
                title=f"🏆 Reward Details: {reward.reward_name}",
                color=0xFFD700
            )

            # Always visible
            embed.add_field(name="🆔 ID", value=reward.reward_id, inline=True)
            embed.add_field(name="📂 Type", value=reward.reward_type, inline=True)
            embed.add_field(name="📈 Number Granted", value=str(reward.number_granted), inline=True)
            embed.add_field(name="✏️ Description", value=reward.description or "*None*", inline=False)

            # Badge-specific
            if reward.reward_type == "badge":
                embed.add_field(name="🏷️ Emoji", value=reward.emoji or "*None*", inline=True)

            # Preset-specific
            if reward.reward_type == "preset":
                embed.add_field(name="📦 Stackable", value="✅" if reward.stackable else "❌", inline=True)

                if reward.use_channel_id and reward.use_message_id:
                    link = f"https://discord.com/channels/{interaction.guild.id}/{reward.use_channel_id}/{reward.use_message_id}"
                    embed.add_field(name="📢 Preset Channel", value=f"<#{reward.use_channel_id}>", inline=True)
                    embed.add_field(name="🔗 Preset Message", value=f"[View Preset]({link})", inline=True)
                else:
                    embed.add_field(name="📢 Preset Channel", value="*Not Published*", inline=True)
                    embed.add_field(name="🔗 Preset Message", value="*Not Published*", inline=True)

            embed.add_field(name="👩‍💻 Created / Edited By", value=created_edited, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)


    # === REWARD LOGS ===
    @admin_or_mod_check()
    @app_commands.describe(
        action="Filter logs by action type (create, edit, delete)",
        moderator="Filter logs by moderator (optional)"
    )
    @app_commands.command(name="logs", description="Show logs of reward creation, edits, and deletion.")
    async def reward_logs(
        self,
        interaction: Interaction,
        action: Optional[str] = None,
        moderator: Optional[discord.User] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            logs = rewards_crud.get_reward_logs(
                session,
                action=action,
                performed_by=str(moderator.id) if moderator else None
            )

            if not logs:
                await interaction.followup.send("❌ No logs found with those filters.")
                return

            pages = []
            for i in range(0, len(logs), LOGS_PER_PAGE):
                chunk = logs[i:i+LOGS_PER_PAGE]
                embed = discord.Embed(
                    title=f"📜 Reward Logs ({i+1}-{i+len(chunk)}/{len(logs)})",
                    color=discord.Color.orange()
                )
                for log in chunk:
                    label = f"Reward `{log.reward_id}`" if log.reward_id else "Deleted Reward"
                    entry_str = format_log_entry(
                        action=log.action,
                        performed_by=log.performed_by,
                        timestamp=log.timestamp,
                        description=log.description,
                        label=label
                    )
                    embed.add_field(name="\n", value=entry_str, inline=False)
                pages.append(embed)

        await paginate_embeds(interaction, pages)


    # === PUBLISH PRESET ===
    @admin_or_mod_check()
    @app_commands.describe(
        reward_id="ID of the reward to link the preset to",
        message_link="Link to the message containing the preset content",
        force="Override restrictions for active events"
    )
    @app_commands.command(
        name="publishpreset",
        description="Publish a reward preset to the official preset channel."
    )
    async def publish_preset(
        self,
        interaction: Interaction,
        reward_id: str,
        message_link: str,
        force: bool = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # 1️⃣ Parse message link
        try:
            parts = message_link.strip().split("/")
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
        except Exception:
            await interaction.followup.send("❌ Invalid message link format.")
            return

        # 2️⃣ Fetch reward & active event guard
        with db_session() as session:
            reward = rewards_crud.get_reward(session, reward_id)
            if not reward:
                await interaction.followup.send(f"❌ Reward `{reward_id}` not found.")
                return

        if rewards_crud.reward_is_linked_to_active_event(session, reward_id):
            if reward.use_message_id and not force:
                await interaction.followup.send(
                    "❌ Cannot re-publish a preset for a reward linked to an active event without `--force`."
                )
                return
            if force:
                confirmed = await confirm_action(
                    interaction,
                    f"reward `{reward_id}` linked to an ACTIVE event",
                    "⚠️ **FORCED REPUBLISH** — participants may see changed content!"
                )
                if not confirmed:
                    return

        # 3️⃣ Archive & delete old preset if exists
        if reward.use_header_message_id and reward.use_message_id:
            try:
                old_channel = await self.bot.fetch_channel(int(REWARD_PRESET_CHANNEL_ID))
                old_header = await old_channel.fetch_message(int(reward.use_header_message_id))
                old_preset = await old_channel.fetch_message(int(reward.use_message_id))

                archive_channel = interaction.guild.get_channel(REWARD_PRESET_ARCHIVE_CHANNEL_ID)
                if archive_channel:
                    # Archive header
                    await archive_channel.send(
                        content=(
                            f"📦 **Archived Header** for `{reward.reward_name}` (`{reward.reward_id}`)\n"
                            f"*Originally published on:* {reward.preset_set_at or 'Unknown'}\n\n"
                            f"{old_header.content or ''}"
                        ),
                        embeds=old_header.embeds,
                        files=[await a.to_file() for a in old_header.attachments]
                    )

                    # Archive clean preset
                    await archive_channel.send(
                        content=f"📦 **Archived Preset Content** for `{reward.reward_name}` (`{reward.reward_id}`)",
                        embeds=old_preset.embeds,
                        files=[await a.to_file() for a in old_preset.attachments]
                    )

                # Delete both old messages
                await old_header.delete()
                await old_preset.delete()

            except Exception as e:
                print(f"⚠️ Failed to archive/delete old preset: {e}")

        # 4️⃣ Fetch the NEW preset message from the link
        try:
            source_channel = await self.bot.fetch_channel(channel_id)
            original_message = await source_channel.fetch_message(message_id)
        except Exception:
            await interaction.followup.send("❌ Could not fetch the original preset message.")
            return

        # 5️⃣ Post new header in approved channel
        preset_channel = interaction.guild.get_channel(REWARD_PRESET_CHANNEL_ID)
        if not preset_channel:
            await interaction.followup.send("❌ Official preset channel not found.")
            return

        header_text = (
            f"🏆 **Reward Preset Published**\n"
            f"**Reward:** {reward.reward_name} (`{reward.reward_id}`)\n"
            f"**Published by:** <@{interaction.user.id}>\n"
            f"**Date:** <t:{now_unix()}:F>"
        )
        new_header = await preset_channel.send(content=header_text)

        # 6️⃣ Post new clean preset in approved channel
        new_clean = await preset_channel.send(
            content=original_message.content or None,
            embeds=original_message.embeds,
            files=[await a.to_file() for a in original_message.attachments]
        )

        # 7️⃣ Save both message IDs in DB
        with db_session() as session:
            rewards_crud.publish_preset(
                session=session,
                reward_id=reward_id,
                use_channel_id=REWARD_PRESET_CHANNEL_ID,
                use_message_id=new_clean.id,           # clean preset
                use_header_message_id=new_header.id,   # header
                set_by=str(interaction.user.id)
            )

        # 8️⃣ Confirm to mod
        await interaction.followup.send(f"✅ Preset published for reward `{reward.reward_name}`.")



async def setup(bot):
    await bot.add_cog(AdminRewardCommands(bot))