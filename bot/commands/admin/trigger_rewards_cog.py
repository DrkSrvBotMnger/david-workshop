# bot/cogs/admin/trigger_rewards_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.time_parse_paginate import admin_or_mod_check
from bot.services.event_triggers_service import link_grant_to_trigger

# --- Services (no DB calls in cogs) ---
# Implement these in your services layer if they don't exist yet.
# The service should:
# - validate event/trigger/reward existence & ownership
# - ensure exactly one of (reward_event_key, points) is provided
# - raise ValueError for user-facing validation errors; Exception for unexpected
#
# Suggested signature (adjust to your actual service module):
#   link_grant_to_trigger(
#       event_id: int,
#       trigger_id: int,
#       reward_event_key: str | None,
#       points: int | None,
#       *, stackable: bool, actor_discord_id: int
#   ) -> dict  # returns a small summary for confirmation message


class TriggerRewardsAdmin(commands.Cog):
    """Admin commands to attach grants (reward or points) to triggers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Create a top-level group: /trigger_reward
    trigger_reward = app_commands.Group(
        name="trigger_reward",
        description="Configure reward/points grants linked to a trigger (admin).",
        guild_only=True,
    )

    @admin_or_mod_check()
    @trigger_reward.command(name="add", description="Attach a reward or points to an event trigger.")
    @app_commands.describe(
        event_id="The event ID this trigger belongs to.",
        trigger_id="The trigger ID to attach the grant to.",
        mode="Choose whether to grant a reward or points when this trigger fires.",
        reward_event_key="If mode = reward, the reward_event_key to grant (e.g., 'dlw25-finisher-badge').",
        points="If mode = points, the number of points to grant (e.g., 50)."
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Reward", value="reward"),
            app_commands.Choice(name="Points", value="points"),
        ]
    )
    async def add_trigger_reward(
        self,
        interaction: discord.Interaction,
        event_id: int,
        trigger_id: int,
        mode: app_commands.Choice[str],
        reward_event_key: str | None = None,
        points: int | None = None
    ):
        """
        Attach a grant to an event trigger:
        - mode=Reward -> provide reward_event_key
        - mode=Points -> provide points
        """
        await interaction.response.defer(ephemeral=True)

        selected_mode = mode.value

        # Basic frontend validation to fail fast (service will also validate)
        if selected_mode == "reward":
            if not reward_event_key:
                return await interaction.followup.send(
                    "❌ You picked **Reward** mode but didn’t provide a **reward_event_key**.",
                    ephemeral=True,
                )
            points_payload = None
            reward_payload = reward_event_key
        else:
            # points mode
            if points is None:
                return await interaction.followup.send(
                    "❌ You picked **Points** mode but didn’t provide a **points** amount.",
                    ephemeral=True,
                )
            if points <= 0:
                return await interaction.followup.send(
                    "❌ **points** must be a positive integer.",
                    ephemeral=True,
                )
            reward_payload = None
            points_payload = int(points)

        try:
            # Delegate to service layer
            summary = link_grant_to_trigger(
                event_id=event_id,
                trigger_id=trigger_id,
                reward_event_key=reward_payload,
                points=points_payload,
                actor_discord_id=interaction.user.id,
            )

            # Build a friendly confirmation message from returned summary
            # Expecting summary like:
            # {
            #   "event_id": 123,
            #   "trigger_id": 456,
            #   "trigger_label": "Do Y action X times • Action: 'Post', X=3",
            #   "grant_type": "reward" | "points",
            #   "reward_event_key": "foo" | None,
            #   "points": 50 | None,
            #   "warnings": ["This reward is also in shop", ...]  # optional
            # }
            trigger_label = summary.get("trigger_label") or f"#{summary.get('trigger_id', trigger_id)}"
            grant_bits = (
                f"**Reward** `{summary['reward_event_key']}`"
                if summary.get("grant_type") == "reward"
                else f"**Points** {summary.get('points')}"
            )
            stackable_txt = "Yes" if summary.get("stackable") else "No"

            lines = [
                "✅ **Trigger grant added**",
                f"• **Event:** `{summary.get('event_id', event_id)}`",
                f"• **Trigger:** `{trigger_label}` (id `{summary.get('trigger_id', trigger_id)}`)",
                f"• **Grant:** {grant_bits}",
                f"• **Stackable:** {stackable_txt}",
            ]

            warnings = summary.get("warnings") or []
            if warnings:
                warn_list = "\n".join([f"  • {w}" for w in warnings])
                lines.append("\n⚠️ **Warnings**\n" + warn_list)

            await interaction.followup.send("\n".join(lines), ephemeral=True)

        except ValueError as ve:
            # Validation / business rule error from service
            await interaction.followup.send(f"❌ {ve}", ephemeral=True)
        except Exception as e:
            # Unexpected error
            await interaction.followup.send(
                "❌ An unexpected error occurred while adding the trigger grant. "
                "Please check logs and try again.",
                ephemeral=True,
            )
            # Log to console (or your logger)
            try:
                print(f"[trigger_reward.add] Unexpected error: {e}")
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(TriggerRewardsAdmin(bot))
