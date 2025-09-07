from typing import Optional

import discord
from bot_instance import get_bot

async def get_channel(channel_id):
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

async def get_message(message_id, channel_id):
    """
    Get a specific message from a channel by its ID.
    
    Args:
        message_id (int): The ID of the message to retrieve.
        channel_id (int): The ID of the channel where the message is located.
        
    Returns:
        discord.Message: The message object if found, otherwise None.
    """
    channel = await get_channel(channel_id)
    if not channel:
        return None
    try:
        return await channel.fetch_message(message_id)
    except discord.NotFound:
        return None
    
async def get_user(user_id, guild_id: Optional[int] = None):
    """
    Get a Discord user by their ID.
    
    Args:
        guild_id: Optional guild ID to fetch the user as a member. If not provided, fetches as a global user.
        user_id (int): The ID of the user to retrieve.
        
    Returns:
        discord.User: The user object if found, otherwise None.
    """
    bot = get_bot()
    try:
        if guild_id:
            guild = await get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    return member
                return await guild.fetch_member(user_id)
        user = bot.get_user(user_id)
        if not user:
            user = await bot.fetch_user(user_id)
        return user
    except discord.NotFound:
        return None

async def get_guild(guild_id):
    """
    Get a Discord guild (server) by its ID.

    Args:
        guild_id (int): The ID of the guild to retrieve.

    Returns:
        discord.Guild: The guild object if found, otherwise None.
    """
    bot = get_bot()
    try:
        guild = bot.get_guild(guild_id)
        if not guild:
            guild = await bot.fetch_guild(guild_id)
        return guild
    except discord.NotFound:
        return None
