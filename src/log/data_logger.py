import os
from discord.ext import commands
from log.log_util import load_json, save_json

CHAT_EVENTS_LOG_FILE = './data/chat_events.json'

def log_chat_event(event):
    """
    Logs a chat event to the chat events log file.
    
    Args:
        event (str): The event to log, should be a string describing the event.
    """
    if os.path.exists(CHAT_EVENTS_LOG_FILE):
        all_events = load_json(CHAT_EVENTS_LOG_FILE)
    else:
        all_events = {'events': []}
        
    all_events['events'].append(event)
    save_json(CHAT_EVENTS_LOG_FILE, all_events)
    
def format_message_attachments(message):
    if not message.attachments:
        return []
    return [{
        'url': attachment.url,
        'filename': attachment.filename,
        'size': attachment.size,
        'content_type': attachment.content_type,
        'description': attachment.description if attachment.description else '',
        'height': attachment.height if attachment.height else None,
        'width': attachment.width if attachment.width else None
        } for attachment in message.attachments]

def format_message_stickers(message):
    if not message.stickers:
        return []
    return [{
        'id': sticker.id,
        'name': sticker.name,
        'format': sticker.format,
        'url': sticker.url if sticker.url else '',
        } for sticker in message.stickers]
    
class DataLoggerCog(commands.Cog):
    
    def __init__(self, client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != int(os.getenv('TELEMETRY_CHANNEL_ID')):
            return        
        event = {
            'timestamp': message.created_at.isoformat(),
            'event_type': 'CREATE-MESSAGE',
            'message_id': message.id,
            'author_id': message.author.id,
            'author_name': message.author.name,
            'author_display_name': message.author.display_name,
            'content': message.content,
            'attachments': format_message_attachments(message),
            'stickers': format_message_stickers(message)
        }
        
        log_chat_event(event)
        
    @commands.Cog.listener()   
    async def on_message_edit(self, before, after):
        if before.channel.id != int(os.getenv('TELEMETRY_CHANNEL_ID')):
            return
        event = {
            'timestamp': after.edited_at.isoformat() if after.edited_at else after.created_at.isoformat(),
            'event_type': 'EDIT-MESSAGE',
            'message_id': after.id,
            'author_id': after.author.id,
            'author_name': after.author.name,
            'author_display_name': after.author.display_name,
            'content_before': before.content,
            'content_after': after.content,
            'attachments_before': format_message_attachments(before),
            'attachments_after': format_message_attachments(after),
            'stickers_before': format_message_stickers(before),
            'stickers_after': format_message_stickers(after)
        }
        log_chat_event(event)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.channel.id != int(os.getenv('TELEMETRY_CHANNEL_ID')):
            return
        event = {
            'timestamp': message.created_at.isoformat(),
            'event_type': 'DELETE-MESSAGE',
            'message_id': message.id,
            'author_id': message.author.id,
            'author_name': message.author.name,
            'author_display_name': message.author.display_name,
            'content': message.content,
            'attachments': format_message_attachments(message),
            'stickers': format_message_stickers(message)
        }
        log_chat_event(event)
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.message.channel.id != int(os.getenv('TELEMETRY_CHANNEL_ID')):
            return
        event = {
            'timestamp': reaction.message.created_at.isoformat(),
            'event_type': 'ADD-REACTION',
            'message_id': reaction.message.id,
            'author_id': user.id,
            'author_name': user.name,
            'author_display_name': user.display_name,
            'reaction': str(reaction.emoji),
            'reaction_count': reaction.count,
            'reaction_users': [u.id for u in reaction.users()]
        }
        log_chat_event(event)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if reaction.message.channel.id != int(os.getenv('TELEMETRY_CHANNEL_ID')):
            return
        event = {
            'timestamp': reaction.message.created_at.isoformat(),
            'event_type': 'REMOVE-REACTION',
            'message_id': reaction.message.id,
            'author_id': user.id,
            'author_name': user.name,
            'author_display_name': user.display_name,
            'reaction': str(reaction.emoji),
            'reaction_count': reaction.count,
            'reaction_users': [u.id for u in reaction.users()]
        }
        log_chat_event(event)
        
async def setup(bot):
    await bot.add_cog(DataLoggerCog(bot))        