import os
import time

from token_usage_manager import manager
from util.memory_check import check_memory_before_import

check_memory_before_import("dspy")
import dspy

check_memory_before_import("mlflow")
import mlflow

check_memory_before_import("discord")
import discord
from dotenv import load_dotenv
from model import ChatContext, ChatAction
from data_collector import collect_interaction_data
from model_manager import ModelManager
from tools.tools_manager import TOOLS

mlflow.dspy.autolog()  # pyright: ignore[reportPrivateImportUsage]
mlflow.set_experiment("GePeTo")

load_dotenv()
ENABLE_DATA_LOG = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
DEFAULT_USER_TOKEN_LIMIT = int(os.getenv('DEFAULT_USER_TOKEN_LIMIT', '100000'))


async def act(messages, message):
    start_time = time.time()
    lm = ModelManager.get_lm()
    model = ModelManager.get_current_model_name()
    adapter = ModelManager.get_adapter()

    user_usage = manager.get_user_monthly_usage(message.author.id, model)
    user_limit = manager.get_user_limit(message.author.id, model)
    if user_limit is None:
        manager.set_user_limit(message.author.id, model, monthly_limit=DEFAULT_USER_TOKEN_LIMIT)
        user_limit = manager.get_user_limit(message.author.id, model)

    if user_usage > user_limit.monthly_limit != -1:
        warning_msg = f"Sorry {message.author.display_name}, you have exceeded your monthly token limit for the model '{model}'. Please contact the administrator to increase your limit."
        await message.channel.send(warning_msg)
        if ENABLE_DATA_LOG:
            collect_interaction_data(
                chat_context_data=create_chat_context_data(messages, message),
                prediction_result=warning_msg,
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message="User exceeded token limit",
                model_name=model,
                model_config={
                    'model_name': model,
                    'adapter': adapter.__class__.__name__ if adapter else 'None'
                }
            )
        return None

    context = ChatContext(
        events=messages,
        chat_id=message.channel.id,
        chat_name=message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM" if message.channel.type == discord.ChannelType.private else "unknown-chat",
        chat_type=message.channel.type.name if hasattr(message.channel, 'type') else 'unknown'
    )

    agent = dspy.ReAct(ChatAction, tools=list(TOOLS.values()))

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

    interaction_usage = [call['usage'] for call in lm.history if 'usage' in call]

    for usage in interaction_usage:
        manager.log_usage(
            user_id=message.author.id,
            model=model,
            prompt_tokens=usage.get('prompt_tokens', 0),
            completion_tokens=usage.get('completion_tokens', 0),
            total_tokens=usage.get('total_tokens', 0)
        )

    execution_time_ms = (time.time() - start_time) * 1000

    chat_context_data = create_chat_context_data(messages, message)

    model_config = {
        'model_name': model,
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
                model_name=model,
                model_config=model_config
            )
    except Exception as e:
        print(f"Warning: Failed to collect interaction data: {e}")

    return result


def create_chat_context_data(messages, message):
    return {
        'events': messages,
        'chat_id': message.channel.id,
        'chat_name': message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM" if message.channel.type == discord.ChannelType.private else "unknown-chat",
        'chat_type': message.channel.type.name if hasattr(message.channel, 'type') else 'unknown',
        'user_id': message.author.id,
        'user_name': message.author.display_name,
        'message_id': message.id,
        'message_content': message.content
    }
