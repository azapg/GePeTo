# message_scraper.py
import json
import os
from datetime import datetime
from log.data_logger import format_message_attachments, format_message_stickers

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Configuration
DATA_FILE = "./data/message-samples.json"

def load_existing_data():
    """Load existing message data from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"messages": []}
    return {"messages": []}

def save_data(data):
    """Save data to JSON file with proper formatting"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

def serialize_discord_object(obj):
    """Convert Discord objects to serializable dictionaries"""
    if obj is None:
        return None
    
    # Handle datetime objects first
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # Handle basic types
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    
    # Handle lists
    if isinstance(obj, list):
        return [serialize_discord_object(item) for item in obj]
    
    # Handle Discord flag objects (like MessageFlags)
    if hasattr(obj, 'value') and hasattr(obj, '__class__'):
        class_name = obj.__class__.__name__
        if 'Flag' in class_name:
            return {
                "type": class_name,
                "value": obj.value,
                "readable": str(obj)
            }
    
    # Handle objects with __dict__
    if hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue
            try:
                result[key] = serialize_discord_object(value)
            except Exception as e:
                result[key] = f"<serialization_error: {str(e)}>"
        return result
    
    # Fallback to string representation
    try:
        return str(obj)
    except Exception as e:
        return f"<serialization_error: {str(e)}>"

def extract_message_data(message):
    """Extract comprehensive data from a Discord message"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "message": {
            "id": message.id,
            "content": message.content,
            "clean_content": message.clean_content,
            "created_at": message.created_at.isoformat(),
            "edited_at": message.edited_at.isoformat() if message.edited_at else None,
            "tts": message.tts,
            "mention_everyone": message.mention_everyone,
            "pinned": message.pinned,
            "flags": serialize_discord_object(message.flags),
            "type": str(message.type),
            "system_content": message.system_content,
            "jump_url": message.jump_url,
        },
        "author": {
            "id": message.author.id,
            "name": message.author.name,
            "display_name": message.author.display_name,
            "discriminator": message.author.discriminator,
            "avatar": str(message.author.avatar) if message.author.avatar else None,
            "bot": message.author.bot,
            "system": message.author.system,
            "created_at": message.author.created_at.isoformat(),
            "public_flags": serialize_discord_object(message.author.public_flags),
            # Member-specific properties (if available)
            "nick": getattr(message.author, 'nick', None),
            "premium_since": getattr(message.author, 'premium_since', None).isoformat() if getattr(message.author, 'premium_since', None) else None,
            "joined_at": getattr(message.author, 'joined_at', None).isoformat() if getattr(message.author, 'joined_at', None) else None,
            "roles": [{"id": role.id, "name": role.name, "color": str(role.color), "position": role.position} 
                     for role in getattr(message.author, 'roles', [])],
            "top_role": {"id": message.author.top_role.id, "name": message.author.top_role.name} 
                       if hasattr(message.author, 'top_role') else None,
        },
        "guild": {
            "id": message.guild.id,
            "name": message.guild.name,
            "description": message.guild.description,
            "icon": str(message.guild.icon) if message.guild.icon else None,
            "banner": str(message.guild.banner) if message.guild.banner else None,
            "splash": str(message.guild.splash) if message.guild.splash else None,
            "discovery_splash": str(message.guild.discovery_splash) if message.guild.discovery_splash else None,
            "owner_id": message.guild.owner_id,
            "region": str(message.guild.region) if hasattr(message.guild, 'region') else None,
            "afk_channel_id": message.guild.afk_channel.id if message.guild.afk_channel else None,
            "afk_timeout": message.guild.afk_timeout,
            "verification_level": str(message.guild.verification_level),
            "default_notifications": str(message.guild.default_notifications),
            "explicit_content_filter": str(message.guild.explicit_content_filter),
            "features": message.guild.features,
            "mfa_level": message.guild.mfa_level,
            "system_channel_id": message.guild.system_channel.id if message.guild.system_channel else None,
            "system_channel_flags": serialize_discord_object(message.guild.system_channel_flags),
            "max_presences": message.guild.max_presences,
            "max_members": message.guild.max_members,
            "premium_tier": message.guild.premium_tier,
            "premium_subscription_count": message.guild.premium_subscription_count,
            "preferred_locale": message.guild.preferred_locale,
            "rules_channel_id": message.guild.rules_channel.id if message.guild.rules_channel else None,
            "public_updates_channel_id": message.guild.public_updates_channel.id if message.guild.public_updates_channel else None,
            "vanity_url_code": message.guild.vanity_url_code,
            "created_at": message.guild.created_at.isoformat(),
        },
        "channel": {
            "id": message.channel.id,
            "name": message.channel.name,
            "type": str(message.channel.type),
            "position": getattr(message.channel, 'position', None),
            "topic": getattr(message.channel, 'topic', None),
            "slowmode_delay": getattr(message.channel, 'slowmode_delay', None),
            "nsfw": getattr(message.channel, 'nsfw', None),
            "last_message_id": getattr(message.channel, 'last_message_id', None),
            "bitrate": getattr(message.channel, 'bitrate', None),
            "user_limit": getattr(message.channel, 'user_limit', None),
            "created_at": message.channel.created_at.isoformat(),
            "mention": message.channel.mention,
            "jump_url": getattr(message.channel, 'jump_url', None),
            # Category information
            "category": {
                "id": message.channel.category.id,
                "name": message.channel.category.name,
                "position": message.channel.category.position,
                "nsfw": message.channel.category.nsfw,
            } if message.channel.category else None,
        },
        "mentions": {
            "users": [{"id": user.id, "name": user.name, "display_name": user.display_name} 
                     for user in message.mentions],
            "roles": [{"id": role.id, "name": role.name, "color": str(role.color)} 
                     for role in message.role_mentions],
            "channels": [{"id": channel.id, "name": channel.name, "type": str(channel.type)} 
                        for channel in message.channel_mentions],
            "everyone": message.mention_everyone,
        },
        "attachments": [
            {
                "id": attachment.id,
                "filename": attachment.filename,
                "url": attachment.url,
                "proxy_url": attachment.proxy_url,
                "size": attachment.size,
                "height": attachment.height,
                "width": attachment.width,
                "content_type": attachment.content_type,
                "description": attachment.description,
            } for attachment in message.attachments
        ],
        "embeds": [serialize_discord_object(embed) for embed in message.embeds],
        "reactions": [
            {
                "emoji": str(reaction.emoji),
                "count": reaction.count,
                "me": reaction.me,
                "custom_emoji": reaction.custom_emoji,
            } for reaction in message.reactions
        ],
        "reference": {
            "message_id": message.reference.message_id,
            "channel_id": message.reference.channel_id,
            "guild_id": message.reference.guild_id,
        } if message.reference else None,
        "stickers": [
            {
                "id": sticker.id,
                "name": sticker.name,
                "description": sticker.description,
                "pack_id": sticker.pack_id,
                "format": str(sticker.format),
                "url": sticker.url,
            } for sticker in message.stickers
        ],
        "components": [serialize_discord_object(component) for component in message.components],
        "thread": {
            "id": message.thread.id,
            "name": message.thread.name,
            "archived": message.thread.archived,
            "auto_archive_duration": message.thread.auto_archive_duration,
            "locked": message.thread.locked,
        } if hasattr(message, 'thread') and message.thread else None,
    }
    
    return data

def extract_minimal_message_data(message):
    return {
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

def log_message(message):
    """
    Main function to log a Discord message
    Call this from your bot's on_message event
    """
    try:
        # Load existing data
        all_data = load_existing_data()
        
        # Check if this message already exists (prevent duplicates)
        message_id = message.id
        existing_ids = {msg.get("message", {}).get("id") for msg in all_data["messages"]}
        
        if message_id in existing_ids:
            print(f"⚠️  Message {message_id} already logged, skipping...")
            return True
        
        # Extract comprehensive message data
        message_data = extract_message_data(message)
        
        # Add to the messages array (this appends, doesn't replace)
        all_data["messages"].append(message_data)
        
        # Save back to file
        save_data(all_data)
        
        print(f"✅ Logged message #{len(all_data['messages'])} from {message.author.name} in #{message.channel.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error logging message: {e}")
        import traceback
        traceback.print_exc()  # This will show the full error details
        return False