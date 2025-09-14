from util.discord import get_guild
from .tools_manager import tool


@tool(permissions=["manage_channels"], needs_confirmation=True)
async def create_channel(guild_id: int, name: str, channel_type: str = "text") -> int:
    """
    Create a new channel in a specific guild.

    Args:
        guild_id (int): The ID of the guild where the channel will be created.
        name (str): The name of the new channel.
        channel_type (str): The type of the channel ("text" or "voice"). Default is "text".

    Returns:
        int: The ID of the newly created channel.
    """
    guild = await get_guild(guild_id)
    if not guild:
        raise ValueError(f"Guild with ID {guild_id} not found.")

    if channel_type == "text":
        channel = await guild.create_text_channel(name)
    elif channel_type == "voice":
        channel = await guild.create_voice_channel(name)
    else:
        raise ValueError("Invalid channel type. Use 'text' or 'voice'.")

    return channel.id
