import os
import time
import dspy
import mlflow
import discord
from dotenv import load_dotenv
from model import ChatContext, ChatAction
from data_collector import collect_interaction_data
from model_manager import ModelManager
from tools.tools_manager import TOOLS
from token_manager import get_token_manager, extract_token_usage_from_history

mlflow.dspy.autolog()
mlflow.set_experiment("GePeTo")

load_dotenv()
ENABLE_DATA_LOG = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
async def act(messages, message):
    start_time = time.time()
    
    # Get token manager and check limits before processing
    token_manager = get_token_manager()
    user_id = message.author.id
    guild_id = message.guild.id if message.guild else None
    channel_id = message.channel.id
    
    # Check if user/guild can process request
    can_process, limit_info = token_manager.can_process_request(user_id, guild_id)
    
    if not can_process:
        # Send limit exceeded message
        limit_msg = "❌ **Token limit exceeded!**\n"
        
        if not limit_info["user"]["bypass"] and "usage" in limit_info["user"]:
            user_usage = limit_info["user"]["usage"]
            user_limit = limit_info["user"]["limit"]
            limit_msg += f"**User limit:** {user_usage['total_tokens']:,}/{user_limit:,} tokens used\n"
        
        if guild_id and not limit_info["guild"]["bypass"] and "usage" in limit_info["guild"]:
            guild_usage = limit_info["guild"]["usage"]
            guild_limit = limit_info["guild"]["limit"]
            limit_msg += f"**Guild limit:** {guild_usage['total_tokens']:,}/{guild_limit:,} tokens used\n"
        
        limit_msg += f"Token limits reset in {limit_info.get('user', {}).get('timeframe_days', 30)} days."
        
        await message.channel.send(limit_msg)
        return None

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
    session_id = None
    token_usage_data = []

    try:
        with dspy.context(lm=lm, adapter=adapter):
            result = await agent.acall(context=context)
            
        # Extract token usage from lm.history after successful call
        if hasattr(lm, 'history') and lm.history:
            # Generate a session ID for this interaction
            import uuid
            session_id = str(uuid.uuid4())
            
            # Extract token usage
            token_usage_data = extract_token_usage_from_history(
                lm.history,
                user_id=user_id,
                guild_id=guild_id,
                channel_id=channel_id,
                session_id=session_id
            )
            
            # Record token usage
            if token_usage_data:
                token_manager.record_token_usage(token_usage_data)
                
                # Calculate session totals for logging
                total_completion = sum(usage.completion_tokens for usage in token_usage_data)
                total_prompt = sum(usage.prompt_tokens for usage in token_usage_data)
                total_session = sum(usage.total_tokens for usage in token_usage_data)
                
                print(f"Token usage - Session {session_id}: {total_completion} completion + {total_prompt} prompt = {total_session} total tokens")
                
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

    # Calculate total tokens for data collector (backward compatibility)
    total_tokens_used = sum(usage.total_tokens for usage in token_usage_data) if token_usage_data else None

    try:
        if ENABLE_DATA_LOG:
            collect_interaction_data(
                chat_context_data=chat_context_data,
                prediction_result=result,
                execution_time_ms=execution_time_ms,
                success=success,
                error_message=error_message,
                model_name=current_model,
                model_config=model_config,
                tokens_used=total_tokens_used,  # Pass total tokens to data collector
                cost_estimate=None  # Cost is usually None as mentioned in issue
            )
    except Exception as e:
        print(f"Warning: Failed to collect interaction data: {e}")

    return result
