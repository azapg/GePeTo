import discord
from bot_instance import get_bot

async def _get_channel(channel_id):
    """
    Get a Discord channel by its ID.
    
    Args:
        channel_id (int): The ID of the channel to retrieve.
        
    Returns:
        discord.TextChannel: The channel object if found, otherwise None.
    """
    bot = get_bot()
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            channel = await bot.fetch_channel(channel_id)
        return channel
    except discord.NotFound:
        return None

async def _get_message(message_id, channel_id):
    """
    Get a specific message from a channel by its ID.
    
    Args:
        message_id (int): The ID of the message to retrieve.
        channel_id (int): The ID of the channel where the message is located.
        
    Returns:
        discord.Message: The message object if found, otherwise None.
    """
    channel = await _get_channel(channel_id)
    if not channel:
        return None
    try:
        return await channel.fetch_message(message_id)
    except discord.NotFound:
        return None
    
async def _get_user(user_id):
    """
    Get a Discord user by their ID.
    
    Args:
        user_id (int): The ID of the user to retrieve.
        
    Returns:
        discord.User: The user object if found, otherwise None.
    """
    bot = get_bot()
    try:
        return await bot.fetch_user(user_id)
    except discord.NotFound:
        return None 
