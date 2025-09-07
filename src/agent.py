import os
import time
import dspy
import mlflow
import discord
from dotenv import load_dotenv
from model import ChatContext, ChatAction
from data_collector import collect_interaction_data
from model_manager import ModelManager
from views.confirm import ConfirmView
from tools.tools_manager import tools_with_context, ToolContext
from src.util.discord import get_user

mlflow.dspy.autolog()
mlflow.set_experiment("GePeTo")

load_dotenv()
ENABLE_DATA_LOG = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')


async def permissions_checker(initiator: discord.Message, permissions: list[str]) -> bool:
    # TODO: Will there ever be a need to check permissions in different guilds?
    user = initiator.author
    if isinstance(user, discord.Member):
        user_permissions = user.guild_permissions
        for perm in permissions:
            if not getattr(user_permissions, perm, False):
                return False
        return True

    return False


# TODO: asking for confirmation should maybe be managed by the agent itself.
#  It could for example decide whether to ask in a DM or in the channel where
#  the request originated from.
async def confirmation_requester(initiator: discord.Message, action: str) -> bool:
    """
    Send a confirmation request to the user.
    Args:
        action: The action or tool that needs confirmation
        initiator: The message that initiated the request

    Returns: True if confirmed, False otherwise
    """
    confirmation_view = ConfirmView(initiator=initiator.author.id, action=action)
    await initiator.reply(
        f"GePeTo needs confirmation to perform the following action:\n ```{action}``` \nDo you want to continue?",
        view=confirmation_view, mention_author=True)
    await confirmation_view.wait()
    return confirmation_view.value if confirmation_view.value is not None else False


async def act(messages, message):
    start_time = time.time()

    context = ChatContext(
        events=messages,
        chat_id=message.channel.id,
        chat_name=message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM" if message.channel.type == discord.ChannelType.private else "unknown-chat",
        chat_type=message.channel.type.name if hasattr(message.channel, 'type') else 'unknown'
    )

    tool_context = ToolContext(initiator=message, permissions_checker=permissions_checker,
                               confirmation_sender=confirmation_requester)
    agent = dspy.ReAct(ChatAction, tools=tools_with_context(context=tool_context))

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
        'chat_name': message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM" if message.channel.type == discord.ChannelType.private else "unknown-chat",
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
