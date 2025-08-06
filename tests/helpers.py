# tests/helpers.py
async def invoke_app_command(cmd, cog, *args, **kwargs):
    """Helper to invoke an @app_commands.command-decorated method in tests."""
    return await cmd.callback(cog, *args, **kwargs)
