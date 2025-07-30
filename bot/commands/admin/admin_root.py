from discord import app_commands

admin_group = app_commands.Group(
    name="admin",
    description="Moderator-only commands."
)
