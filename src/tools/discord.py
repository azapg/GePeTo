import os
from .tools_manager import tool
from util.discord import _get_channel, _get_message, _get_user

@tool
async def mark_as_typing(channel_id):
    """
    Mark the bot as typing in a specific channel. Useful to indicate that the bot is processing a request or generating a response.
    This can help improve user experience by showing that the bot is actively working on something.
    This mark is only temporary and does not send any message to the channel.
    The mark disappears after a short period of time, usually around 10 seconds or when the bot sends a message.
    
    This should almost always be used before sending a message, to indicate that the bot is working on a response.
    
    Args:
        channel_id (int): The ID of the channel where the bot should appear as typing.
        
    Returns:
        bool: True if the bot successfully marked as typing, False otherwise.
    """
    channel = await _get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel with ID {channel_id} not found.")
    
    await channel.typing()
    return "Successfully marked as typing in channel {channel_id}."

@tool
async def reply_to_message(message_id, channel_id, content, mention=False):
    """
    Reply to a specific message in a channel.
    Should be used every time there is multiple people in the channel, to avoid confusion.
    Args:
        message_id (int): The ID of the message to reply to.
        channel_id (int): The ID of the channel where the message is located.
        content (str): The content of the reply message.
        mention (bool): Whether to mention the user in the reply. Sometimes useful to get the user's attention.
    """
    message = await _get_message(message_id, channel_id)
    if not message:
        raise ValueError(f"Message with ID {message_id} not found in channel {channel_id}.")
    
    await message.reply(content, mention_author=mention,)
    return "Successfully replied to message {message_id} in channel {channel_id}."

@tool        
async def send_message(channel_id: int, content: str) -> bool:
    """Send a message to a specific channel."""
    channel = await _get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel with ID {channel_id} not found.")
    
    await channel.send(content)
    return "Successfully sent message to channel {channel_id}."

@tool
async def send_private_message(user_id: int, content: str):
    """
    Send a private message to a specific user.
    
    Args:
        user_id (int): The ID of the user to send the message to.
        content (str): The content of the private message.
        
    """
    user = await _get_user(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found.")
    
    await user.send(content)
    return "Successfully sent private message to user {user_id}."

@tool
async def edit_message(message_id, channel_id, content):
    """
    Edit a message sent by GePeTo in a specific channel.
    
    Args:
        message_id (int): The ID of the message to edit.
        channel_id (int): The ID of the channel where the message is located.
        content (str): The new content for the message.
    """
    message = await _get_message(message_id, channel_id)
    if not message:
        raise ValueError(f"Message with ID {message_id} not found in channel {channel_id}.")

    await message.edit(content=content)
    return "Successfully edited message {message_id} in channel {channel_id}."

@tool
async def delete_message(message_id, channel_id):
    """
    Delete a message sent in a specific channel.
    
    Args:
        message_id (int): The ID of the message to delete.
        channel_id (int): The ID of the channel where the message is located.

    """
    message = await _get_message(message_id, channel_id)
    if not message:
        raise ValueError(f"Message with ID {message_id} not found in channel {channel_id}.")
    
    if message.author.id != int(os.getenv('BOT_ID')):
        raise ValueError(f"Message with ID {message_id} was not sent by GePeTo. You can't delete other people's messages!")

    await message.delete()
    return "Successfully deleted message {message_id} in channel {channel_id}."

@tool    
async def react_to_message(message_id, channel_id, emoji_id):
    """
    React to a specific message in a channel with an emoji.
    
    Args:
        message_id (int): The ID of the message to react to.
        channel_id (int): The ID of the channel where the message is located.
        emoji_id (str): The ID of the emoji to use for the reaction.
        
    """
    message = await _get_message(message_id, channel_id)
    if not message:
        raise ValueError(f"Message with ID {message_id} not found in channel {channel_id}.")
    emoji = await message.guild.fetch_emoji(emoji_id);
    await message.add_reaction(emoji) 
    return "Successfully reacted to message {message_id} in channel {channel_id} with emoji {emoji_id}."
