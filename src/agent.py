import os
import time

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

mlflow.dspy.autolog() # pyright: ignore[reportPrivateImportUsage]
mlflow.set_experiment("GePeTo")

load_dotenv()
ENABLE_DATA_LOG = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')


async def act(messages, message):
    start_time = time.time()

    context = ChatContext(
        events=messages,
        chat_id=message.channel.id,
        chat_name=message.channel.name if message.channel.type == discord.ChannelType.text else message.author.display_name + "DM" if message.channel.type == discord.ChannelType.private else "unknown-chat",
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
