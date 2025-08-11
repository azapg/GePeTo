import dspy
import os
from typing import List, Any
import pydantic
import mlflow
import discord
from dotenv import load_dotenv
import time
from data_collector import collect_interaction_data
from model_manager import ModelManager

from tools.tools_manager import TOOLS

mlflow.dspy.autolog()
mlflow.set_experiment("DSPy")

load_dotenv()

ENABLE_DATA_LOG = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    
class ChatEvent(pydantic.BaseModel):
    """
    Model representing any chat event.
    For now, this will accept any dictionary structure,
    making it highly flexible and less prone to validation errors
    if the incoming event structure varies or is not fully defined yet.
    """
    timestamp: str
    event_type: str
    class Config:
        extra = 'allow'
 

class ChatContext(pydantic.BaseModel):
    """"Context for the chat model, including general information of this chat and the latest events."""
    events: List[Any]
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
    start_time = time.time()
    
    context = ChatContext(
        events=messages, 
        chat_id=message.channel.id, 
        chat_name=message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM"  if message.channel.type == discord.ChannelType.private else "unknown-chat", 
        chat_type=message.channel.type.name if hasattr(message.channel, 'type') else 'unknown'
    )

    agent = dspy.ReAct(ChatAction, tools=list(TOOLS.values()))
    
    lm = ModelManager.get_lm()
    adapter = ModelManager.get_adapter()
    
    success = True
    error_message = None
    result = None
    
    try:
        with dspy.context(lm=lm, adapter=adapter):
            result = await agent.acall(context=context)
    except Exception as e:
        success = False
        error_message = str(e)
        print(f"Error in act() function: {e}")
        
    execution_time_ms = (time.time() - start_time) * 1000
    
    chat_context_data = {
        'events': messages,
        'chat_id': message.channel.id,
        'chat_name': message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM"  if message.channel.type == discord.ChannelType.private else "unknown-chat",
        'chat_type': message.channel.type.name if hasattr(message.channel, 'type') else 'unknown',
        'user_id': message.author.id,
        'user_name': message.author.display_name,
        'message_id': message.id,
        'message_content': message.content
    }
    
    current_model = ModelManager.get_current_model_name()
    model_config = {
        'model_name': current_model,
        'adapter': adapter.__class__.__name__ if adapter else 'None'
    }
    
    try:
        if ENABLE_DATA_LOG:
            collect_interaction_data(
                chat_context_data=chat_context_data,
                prediction_result=result,
                execution_time_ms=execution_time_ms,
                success=success,
                error_message=error_message,
                model_name=current_model,
                model_config=model_config
            )
    except Exception as e:
        print(f"Warning: Failed to collect interaction data: {e}")
    
    return result

