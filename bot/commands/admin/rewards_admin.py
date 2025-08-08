import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from typing import Optional

from bot.crud import rewards_crud
from bot.config import REWARDS_PER_PAGE, LOGS_PER_PAGE, REWARD_PRESET_CHANNEL_ID, REWARD_PRESET_ARCHIVE_CHANNEL_ID, CUSTOM_DISCORD_EMOJI, UNICODE_EMOJI, BADGE_TYPES, STACKABLE_TYPES, PUBLISHABLE_REWARD_TYPES
from bot.utils.time_parse_paginate import admin_or_mod_check, confirm_action, paginate_embeds, format_discord_timestamp, format_log_entry, now_unix, parse_message_link
from db.database import db_session


class AdminRewardCommands(commands.GroupCog, name="admin_reward"):
    """Admin commands for managing rewards."""

    def __init__(self, bot):
        self.bot = bot

    
    # === HELPERS ===
    # Auto-prefix reward keys
    @staticmethod
    def ensure_reward_prefix(
        reward_key: str, 
        reward_type: str
    ) -> str:
        """Ensures the reward_key has the correct prefix for its type."""
        
        prefix_map = {
            "title": "t_",
            "badge": "b_",
            "preset": "p_",
            "dynamic": "d_"
        }
        prefix = prefix_map.get(reward_type.lower())
        
        if prefix and not reward_key.lower().startswith(prefix):
            return f"{prefix}{reward_key}"
        return reward_key

        
    # Check emoji is valid
    @staticmethod
    def is_valid_emoji(
        value: Optional[str]
    ) -> bool:
        """Check if the given value is a valid emoji (Unicode or Discord custom)."""

        if not value:
            return False
        else:
            return bool(CUSTOM_DISCORD_EMOJI.match(value) or UNICODE_EMOJI.match(value))
            

    
    # === CREATE REWARD ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode for the reward (prefix auto-added: b_, d_, p_, t_ depending on type)",
        reward_type="Type of reward: title, badge, preset",
        name="Display name of the reward",
        description="Optional description for the reward",
        emoji="Optional emoji for badge rewards (required if type=badge)",
        stackable="Whether this reward can stack in inventory (default: False)"
    )
    @app_commands.rename(reward_type="type")
    @app_commands.command(name="create", description="Create a new reward.")
    async def create_reward(
        self,
        interaction: Interaction,
        shortcode: str,
        reward_type: str,
        name: str,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
        stackable: Optional[bool] = False
    ):
        """Create a new reward with the given details."""
        
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Ensure correct prefix for the type
        reward_key = self.ensure_reward_prefix(shortcode, reward_type)

        # Enforce emoji requirement for badges
        if reward_type.lower() == "badge" and not self.is_valid_emoji(emoji):
            await interaction.followup.send("❌ Badge rewards must have an emoji.")
            return
            
        # Enforce emoji rule
        if reward_type.lower() not in BADGE_TYPES:
            emoji = None

        # Enforce stackable rule
        if reward_type.lower() not in STACKABLE_TYPES:
            stackable = False

        with db_session() as session:
            if rewards_crud.get_reward_by_key(
                session=session, 
                reward_key=shortcode
            ):
                await interaction.followup.send(f"❌ Reward `{reward_key}` already exists.")
                return

            reward_create_data={
                "reward_key": reward_key,
                "reward_type": reward_type.lower(),
                "reward_name": name,
                "reward_description": description,
                "emoji": emoji,
                "is_stackable": stackable,
                "created_by": str(interaction.user.id)
            }
            
            rewards_crud.create_reward(
                session=session,
                reward_create_data=reward_create_data
            )

        await interaction.followup.send(f"✅ Reward `{name}` created with shortcode `{reward_key}`.")


    # === EDIT REWARD ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode (with the prefix) of the reward to edit",
        name="New name for the reward (optional)",
        description="New description for the reward (optional)",
        emoji="New emoji (optional)",
        stackable="Set True/False to change stackability (optional)",
        reason="Optional reason for editing (will be logged)",
        force="Override restrictions for active events"
    )
    @app_commands.command(name="edit", description="Edit an existing reward.")
    async def edit_reward(
        self,
        interaction: Interaction,
        shortcode: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
        stackable: Optional[bool] = None,
        reason: Optional[str] = None,
        force: bool = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        with db_session() as session:
            reward = rewards_crud.get_reward_by_key(
                session=session, 
                reward_key=shortcode
            )
            if not reward:
                await interaction.followup.send(f"❌ Reward `{shortcode}` not found.")
                return

            if rewards_crud.reward_is_linked_to_active_event(session, shortcode):
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
                        f"reward `{shortcode}` linked to an ACTIVE event",
                        "force_update",
                        "⚠️ **FORCED OVERRIDE** — this may impact participants!")
                    if not confirmed:
                        return

            # Enforce emoji rule
            if reward.reward_type.lower() not in BADGE_TYPES:
                emoji = None
                # Enforce emoji requirement for badges
            if reward.reward_type.lower() in BADGE_TYPES and not self.is_valid_emoji(emoji):
                await interaction.followup.send("❌ Badge rewards must have a valid emoji.")
                return

            # Enforce stackable rule
            if reward.reward_type.lower() not in STACKABLE_TYPES:
                stackable = None
                
            reward_update_data = {}
            if name:
                reward_update_data["reward_name"] = name
            if description is not None:
                reward_update_data["reward_description"] = description
            if emoji is not None:
                reward_update_data["emoji"] = emoji
            if stackable is not None:
                reward_update_data["is_stackable"] = stackable

            if not reward_update_data:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return

            reward_update_data["modified_by"] = str(interaction.user.id)
            
            rewards_crud.update_reward(
                session=session,
                reward_key=shortcode,
                reward_update_data=reward_update_data,
                reason=reason,
                forced=force
            )

        await interaction.followup.send(f"✅ Reward `{shortcode}` updated successfully.")


    # === DELETE REWARD ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode (with the prefix) of the reward to delete",
        reason="Reason for deleting (will be logged)",
        force="Override restrictions for active events"
    )
    @app_commands.command(name="delete", description="Delete a reward.")
    async def delete_reward(
        self, 
        interaction: Interaction, 
        shortcode: str,
        reason: str,
        force: bool = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward = rewards_crud.get_reward_by_key(
                session=session, 
                reward_key=shortcode
            )
            
            if not reward:
                await interaction.edit_original_response(content=f"❌ Reward `{shortcode}` not found.",view=None)
                return

        confirmed = await confirm_action(
            interaction=interaction, 
            item_name=f"reward `{shortcode}`", 
            item_action="delete",
            reason="Removal"
        )
        
        if not confirmed:
            await interaction.edit_original_response(content="❌ Deletion cancelled or timed out.", view=None)
            return
        else:
            if rewards_crud.reward_is_linked_to_active_event(
                session=session, 
                reward_key=shortcode
            ):
                if not force:
                    await interaction.edit_original_response(content=
                        "❌ Cannot delete a reward linked to an active event without `--force`.", view=None)
                    return
                else:    
                    confirmed = await confirm_action(
                        interaction=interaction,
                        item_name=f"reward `{shortcode}` linked to an ACTIVE event",
                        item_action="force_delete",
                        reason="⚠️ **FORCED DELETE** — this will impact participants!"
                    )
                    
                    if not confirmed:
                            await interaction.edit_original_response(content="❌ Deletion cancelled or timed out.", view=None)
                            return


        with db_session() as session:
            rewards_crud.delete_reward(
                session=session,
                reward_key=shortcode,
                performed_by=str(interaction.user.id),
                reason=reason,
                forced=force
            )

        await interaction.edit_original_response(content=f"✅ Reward `{shortcode}` deleted.", view=None)


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

        mod_by_discord_id = str(mod.id) if mod else None

        with db_session() as session:
            rewards = rewards_crud.get_all_rewards(
                session=session,
                reward_type=type,
                mod_by_discord_id=mod_by_discord_id,
                reward_name=name
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
                        f"**Shortcode:** `{r.reward_key}` | **Name:** {r.reward_name} | **Type:** {r.reward_type}",
                        f"👤 Last updated by: {updated_by}",
                        f"🕒 On: {formatted_time}",
                    ]
                    embed.add_field(name="\n", value="\n".join(lines), inline=False)
                pages.append(embed)

        await paginate_embeds(interaction, pages)


    # === SHOW REWARD DETAILS ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode (with the prefix) of the reward to view in detail"
    )
    @app_commands.command(name="show", description="Show full details of a reward.")
    async def show_reward(
        self, 
        interaction: Interaction, 
        shortcode: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            reward = rewards_crud.get_reward_by_key(
                session=session, 
                reward_key=shortcode
        )
            if not reward:
                await interaction.followup.send(f"❌ Reward `{shortcode}` not found.")
                return

            created_edited = f"By: <@{reward.created_by}> at {format_discord_timestamp(reward.created_at)}"
            if reward.modified_by:
                created_edited += f"\nLast: <@{reward.modified_by}> at {format_discord_timestamp(reward.modified_at)}"

            embed = Embed(
                title=f"🏆 Reward Details: {reward.reward_name}",
                color=0xFFD700
            )

            # Always visible
            embed.add_field(name="🆔 Shortcode", value=reward.reward_key, inline=True)
            embed.add_field(name="📂 Type", value=reward.reward_type, inline=True)
            embed.add_field(name="📈 Number Granted", value=str(reward.number_granted), inline=True)
            embed.add_field(name="✏️ Description", value=reward.reward_description or "*None*", inline=False)

            # Badge-specific
            if reward.reward_type == "badge":
                embed.add_field(name="🏷️ Emoji", value=reward.emoji or "*None*", inline=True)

            # Preset-specific
            if reward.reward_type == "preset":
                embed.add_field(name="📦 Stackable", value="✅" if reward.is_stackable else "❌", inline=True)

                if reward.use_channel_discord_id and reward.use_message_discord_id:
                    link = f"https://discord.com/channels/{interaction.guild.id}/{reward.use_channel_discord_id}/{reward.use_message_discord_id}"
                    embed.add_field(name="📢 Preset Channel", value=f"<#{reward.use_channel_discord_id}>", inline=True)
                    embed.add_field(name="🔗 Preset Message", value=f"[View Preset]({link})", inline=True)
                else:
                    embed.add_field(name="📢 Preset Channel", value="*Not Published*", inline=True)
                    embed.add_field(name="🔗 Preset Message", value="*Not Published*", inline=True)

            embed.add_field(name="👩‍💻 Created / Edited By", value=created_edited, inline=False)

            await interaction.followup.send(embed=embed)


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
                session=session,
                log_action=action,
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
                        log_action=log.log_action,
                        performed_by=log.performed_by,
                        performed_at=log.performed_at,
                        log_description=log.log_description,
                        label=label
                    )
                    embed.add_field(name="\n", value=entry_str, inline=False)
                pages.append(embed)

        await paginate_embeds(interaction, pages)


    # === PUBLISH PRESET ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode (with the prefix) of the reward to link the preset to",
        message_link="Link to the message containing the preset content",
        force="Override restrictions for active events"
    )
    @app_commands.command(name="publishpreset", description="Publish a reward preset to the official preset channel."
    )
    async def publish_preset(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        message_link: str,
        force: bool = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # 1️⃣ Parse message link
        channel_id, message_id = parse_message_link(message_link)
   
        # 2️⃣ Fetch reward & save old IDs
        with db_session() as session:
            reward = rewards_crud.get_reward_by_key(
                session=session, 
                reward_key=shortcode
            )
            if not reward:
                await interaction.followup.send(f"❌ Reward `{shortcode}` not found.")
                return

            if reward.reward_type.lower() not in PUBLISHABLE_REWARD_TYPES:
                await interaction.followup.send(
                    f"❌ Reward `{shortcode}` is not a publishable type of reward."
                )
                return

            header_id_old = reward.use_header_message_discord_id
            preset_id_old = reward.use_message_discord_id
            reward_name = reward.reward_name
            reward_key = reward.reward_key
            preset_at = reward.preset_at

            # Check active event rule
            if rewards_crud.reward_is_linked_to_active_event(
                session=session, 
                reward_key=reward_key
            ):
                if reward.use_message_id and not force:
                    await interaction.followup.send(
                        "❌ Cannot re-publish a preset for a reward linked to an active event without `--force`."
                    )
                    return
                if force:
                    confirmed = await confirm_action(
                        interaction,
                        f"reward `{reward_key}` linked to an ACTIVE event",
                        "force_update",
                        "⚠️ **FORCED REPUBLISH** — participants may see changed content!"
                    )
                    if not confirmed:
                        return

        # 3️⃣ Archive & delete old preset if exists
        if header_id_old and preset_id_old:
            try:
                old_channel = await self.bot.fetch_channel(int(REWARD_PRESET_CHANNEL_ID))
                old_header = await old_channel.fetch_message(int(header_id_old))
                old_preset = await old_channel.fetch_message(int(preset_id_old))

                archive_channel = interaction.guild.get_channel(REWARD_PRESET_ARCHIVE_CHANNEL_ID)
                if archive_channel:
                    # Archive header
                    await archive_channel.send(
                        content=(
                            f"📦 **Archived Header** for `{reward_name}` (`{reward_key}`)\n"
                            f"*Originally published on:* {preset_at or 'Unknown'}\n\n"
                            f"{old_header.content or ''}"
                        ),
                        embeds=old_header.embeds,
                        files=[await a.to_file() for a in old_header.attachments]
                    )

                    # Archive clean preset
                    content_text = f"📦 **Archived Preset Content** for `{reward_name}` (`{reward_key}`)"
                    content_text = f"{content_text} \n{old_preset.content}"
                    await archive_channel.send(
                        content=content_text,
                        embeds=old_preset.embeds if old_preset.embeds else [],
                        files=[await a.to_file() for a in old_preset.attachments] if old_preset.attachments else []
                    )

                # Delete both old messages from approved channel
                await old_header.delete()
                await old_preset.delete()

            except Exception as e:
                print(f"⚠️ Failed to archive/delete old preset: {e}")
        else:
            print(f"No old preset to archive for `{reward_key}` — this is the first publish.")

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
            f"**Reward:** `{reward_name}` (`{reward_key}`)\n"
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

        # 🔹 Delete the original staging message
        try:
            await original_message.delete()
        except discord.Forbidden:
            print("❌ Bot is missing permission to delete the original message.")
        except discord.HTTPException as e:
            print(f"⚠️ Failed to delete original message: {e}")

        # 7️⃣ Save both message IDs in DB
        with db_session() as session:
            rewards_crud.publish_preset(
                session=session,
                reward_key=reward_key,
                use_channel_discord_id=REWARD_PRESET_CHANNEL_ID,
                use_message_discord_id=new_clean.id,           # clean preset
                use_header_message_discord_id=new_header.id,   # header
                set_by_discord_id=str(interaction.user.id),
                forced=force
            )

        # 8️⃣ Confirm to mod
        await interaction.followup.send(f"✅ Preset published for reward `{reward_name}` (`{reward_key}`).")


# Future commands to implement:

# /admin_reward settemplate → Define the usage template for an interactive reward.
# example: /admin_reward settemplate reward_id:hug template:"{user} hugs {target}" allowed_params:"target"

# /admin_reward addmedia → Add a media file or URL to the reward’s media pool.
# example: /admin_reward addmedia reward_id:hug media_url:https://...

# /admin_reward listmedia → View all stored media for a reward.

# /admin_reward deletemedia → Remove a media entry.


async def setup(bot):
    await bot.add_cog(AdminRewardCommands(bot))