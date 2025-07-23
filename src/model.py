import dspy
import os
from typing import List, Dict, Any, Optional
import pydantic
import mlflow
import discord
from dotenv import load_dotenv
from bot_instance import get_bot
from dspy.adapters import JSONAdapter
mlflow.dspy.autolog()
mlflow.set_experiment("DSPy")

load_dotenv()

# ModelManager for dynamic model switching
class ModelManager:
    _model_map = {
        'kimi-k2-free': {
            'name': 'openai/moonshotai/kimi-k2-instruct',
            'api_key': os.getenv('GROQ_API_KEY_FREE'),
            'api_base': 'https://api.groq.com/openai/v1',
        },
        'kimi-k2-paid': {
            'name': 'openai/moonshotai/kimi-k2-instruct',
            'api_key': os.getenv('GROQ_API_KEY_PAID'),
            'api_base': 'https://api.groq.com/openai/v1',
        },
        'gpt-4o': {
            'name': 'openai/gpt-4o',
            'api_key': os.getenv('OPENAI_API_KEY'),
            'api_base': 'https://api.openai.com/v1',
        },
        'gpt-4-mini': {
            'name': 'openai/gpt-4.1-mini-2025-04-14',
            'api_key': os.getenv('OPENAI_API_KEY'),
            'api_base': 'https://api.openai.com/v1',
        },
        'gemini': {
            'name': 'openai/gemini-2.0-flash-lite',
            'api_key': os.getenv('GOOGLE_API_KEY'),
            'api_base': 'https://generativelanguage.googleapis.com/v1beta/openai/',
        },
        'llama3': {
            'name': 'openai/llama3.3-70b',
            'api_key': os.getenv('CEREBRAS_API_KEY'),
            'api_base': 'https://api.cerebras.ai/v1',
        },
        'meta-llama': {
            'name': 'openai/meta-llama/Llama-3.3-70B-Instruct',
            'api_key': os.getenv('NEBIUS_API_KEY'),
            'api_base': 'https://api.studio.nebius.com/v1/',
        },
        'gemma': {
            'name': 'ollama_chat/gemma3:1b',
            'api_key': '',
            'api_base': 'http://localhost:11434',
        },
    }
    _current_model: str = 'kimi-k2-paid'
    _adapter = JSONAdapter()

    @classmethod
    def get_model_names(cls):
        return list(cls._model_map.keys())

    @classmethod
    def get_current_model_name(cls):
        return cls._current_model

    @classmethod
    def set_model(cls, model_name: str) -> bool:
        if model_name not in cls._model_map:
            return False
        cls._current_model = model_name
        return True

    @classmethod
    def get_lm(cls):
        cfg = cls._model_map[cls._current_model]
        return dspy.LM(cfg['name'], api_key=cfg['api_key'], api_base=cfg['api_base'])

    @classmethod
    def get_adapter(cls):
        return cls._adapter

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
        
DOCS = {}

def search(query: str, k: int) -> list[str]:
    results = dspy.ColBERTv2(url='http://20.102.90.50:2017/wiki17_abstracts')(query, k=k)
    results = [x['text'] for x in results]

    for result in results:
        title, text = result.split(" | ", 1)
        DOCS[title] = text

    return results

def search_wikipedia(query: str) -> list[str]:
    """Returns top-5 results and then the titles of the top-5 to top-30 results."""

    topK = search(query, 30)
    titles, topK = [f"`{x.split(' | ')[0]}`" for x in topK[5:30]], topK[:5]
    return topK + [f"Other retrieved pages have titles: {', '.join(titles)}."]

def lookup_wikipedia(title: str) -> str:
    """Returns the text of the Wikipedia page, if it exists."""

    if title in DOCS:
        return DOCS[title]

    results = [x for x in search(title, 10) if x.startswith(title + " | ")]
    if not results:
        return f"No Wikipedia page found for title: {title}"
    return results[0]

async def send_message(channel_id: int, content: str) -> bool:
    """Send a message to a specific channel."""
    channel = await _get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel with ID {channel_id} not found.")
    
    await channel.send(content)
    return "Successfully sent message to channel {channel_id}."
    

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
    
async def get_image_context(url):
    """
    Get the context of an image from a URL.
    
    Args:
        url (str): The URL of the image.
        
    Returns:
        str: The context of the image.
    """
    describe = dspy.Predict("image -> description")
    result = describe(image=dspy.Image.from_url(url))
    return result.description

# class Attachment(pydantic.BaseModel):
#     """Model representing an attachment in a chat event."""
#     url: str
#     filename: str
#     size: int
#     content_type: str
#     description: Optional[str] = None
#     height: Optional[int] = None
#     width: Optional[int] = None

# class Sticker(pydantic.BaseModel):
#     """Model representing a sticker in a chat event."""
#     id: int
#     name: str
#     format: List[Union[str, int]] # Format can be a string (e.g., "png") or an int (e.g., 1)
#     url: str

# class ChatEvent(pydantic.BaseModel):
#     """Model representing a chat event (message, edit, delete, etc.)."""
#     timestamp: str
#     event_type: str = pydantic.Field(..., pattern="^(CREATE-MESSAGE|EDIT-MESSAGE|DELETE-MESSAGE)$")
#     message_id: int
#     author_id: int
#     author_name: str
#     author_display_name: str
#     channel_id: Optional[int] = None # Assuming channel_id might not always be present or relevant for all event types

#     # Fields specific to CREATE-MESSAGE and DELETE-MESSAGE
#     content: Optional[str] = None
#     attachments: Optional[List[Attachment]] = None
#     stickers: Optional[List[Sticker]] = None

#     # Fields specific to EDIT-MESSAGE
#     content_before: Optional[str] = None
#     content_after: Optional[str] = None
#     attachments_before: Optional[List[Attachment]] = None
#     attachments_after: Optional[List[Attachment]] = None
#     stickers_before: Optional[List[Sticker]] = None
#     stickers_after: Optional[List[Sticker]] = None
    
class ChatEvent(pydantic.BaseModel):
    """
    Model representing any chat event.
    For now, this will accept any dictionary structure,
    making it highly flexible and less prone to validation errors
    if the incoming event structure varies or is not fully defined yet.
    """
    # Using extra='allow' tells Pydantic to allow any extra fields
    # not explicitly defined in the model.
    # We'll just define the core fields that are guaranteed to be there,
    # or keep it minimal if you want to allow anything.
    # For maximum flexibility, you can even just pass **kwargs to a base model.

    # Example: If you at least want these core fields to be present
    timestamp: str
    event_type: str
    # If you want to accept *anything* and deal with it later, you can use **data: dict
    # This will capture all the incoming key-value pairs as a dictionary.

    # This is a more lenient approach than strictly defining all possible fields.
    # If you remove all fields from ChatEvent and just want to accept raw dictionaries,
    # you could even define Events as List[Dict[str, Any]] directly in ChatContext.
    
    class Config:
        extra = 'allow' # This is key to allowing undefined fields
 

class ChatContext(pydantic.BaseModel):
    """"Context for the chat model, including general information of this chat and the latest events."""
    events: List[Any] # Now accepts a list of generic dictionaries for events
    chat_id: int
    chat_name: str
    chat_type: str

class ChatAction(dspy.Signature):
    """You are a smart chatbot that generates responses based on the provided context.
    Your name is GePeTo, you try to mimick user's writing style and you are very friendly.
    You should always respond in a way that your messages fit the context and style of the conversation.
    You can also be helpful by providing additional information or asking clarifying questions, but remember
    you are a friendly chatbot, not just an assistant.
    
    The server you are in is a Discord server, so you should be aware of the Discord context. The server name is
    Coreacraft, the user "alamagain" (759129351370833940) is the creator of GePeTo. The creator of the server itself is adriiianhhh (789685658872446978), segmx (455122269514104852) is an administrator.
    
    You can use multiple tools to interact with Discord, such as sending, editing or deleting messages,
    reacting, getting image context, you can reply directly to messages, and you can also
    access the message history to understand the context of the conversation.
    
    You always mark yourself as typing before sending a message, to indicate that you are processing the request.
    You also reply to messages when there are multiple people in the channel, to avoid confusion.
    You never respond in your reasoning, you only respond with the tools you use.
    Only use your reasoning to decide which tools to use and how to use them.
    
    Remember to always output all the fields in the output, even if they are not used.
    Don't ever forget to use [next_thought, next_tool_name, next_tool_args]
    to indicate the next action you will take.
    
    In discord you mention users by their ID, so you can use <@USER_ID> to mention a user.
    You can also use emojis by their ID, like <:emoji_name:emoji_id>.
    Don't mention people randomly because it can be annoying, only mention them when you are replying to their message or when you need their attention.
    
    Large messages often spam the chat, use short answers, single sentences if possible. Do not overuse emojis if others don't use them. Only use emojis if they are really necessary or the situation asks for it
    That's part of mimicking the enviorment behaviour.
    
    If the chat is in spanish, reply in spanish.
    Always consider to use all of your tools, not just send and reply. Try to react to messages, edit and delete yours to make jokes.
    You can also use markdown format for titles, bold, italics, and "-#" before a sentence for small text.
    
    When users are tagging you too much, enter in a relax state. State that you can't be replying to so many messages and suggest going to private chats instead. That would keep the chat more managable in high use hours.
    
    Remember: DO NOT SPAM THE CHAT, KEEP IT FUN BUT YOU DON'T WANT TO HAVE HUNDREDS OF MESSAGES SPAMMING.
    """
    
    context: ChatContext = dspy.InputField(desc="The context of the chat, including messages and chat information.")
    done: bool = dspy.OutputField(desc="Whetever GePeTo could perform all its actions successfully.")

async def act(messages, message):
    context = ChatContext(
        events=messages, 
        chat_id=message.channel.id, 
        chat_name=message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM"  if message.channel.type == discord.ChannelType.private else "unknown-chat", 
        chat_type=message.channel.type.name if hasattr(message.channel, 'type') else 'unknown'
    )

    agent = dspy.ReAct(ChatAction, tools=[
        send_message,
        send_private_message,
        edit_message,
        delete_message,
        reply_to_message,
        react_to_message,
        get_image_context,
        mark_as_typing,
        search,
        search_wikipedia,
        lookup_wikipedia,
    ])
    # Use the current model context
    lm = ModelManager.get_lm()
    adapter = ModelManager.get_adapter()
    with dspy.context(lm=lm, adapter=adapter):
        result = await agent.acall(context=context)

# Export ModelManager and get_current_model_name for bot.py
get_current_model_name = ModelManager.get_current_model_name
set_model = ModelManager.set_model
get_model_names = ModelManager.get_model_names