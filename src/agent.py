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
from token_manager_v2 import get_token_manager, extract_token_usage_from_history

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
    
    # Get current model name for limit checking
    current_model = ModelManager.get_current_model_name()
    
    # Get user roles if in a guild
    user_roles = None
    if guild_id and hasattr(message.author, 'roles'):
        user_roles = [role.id for role in message.author.roles]
    
    # Check if user/guild can process request
    can_process, limit_info = token_manager.can_process_request(user_id, guild_id, current_model, 0, user_roles)
    
    if not can_process:
        # Send limit exceeded message
        limit_msg = "❌ **Token limit exceeded!**\n"
        
        user_info = limit_info.get("user", {})
        guild_info = limit_info.get("guild", {})
        
        # Handle user limit messages
        if user_info.get("charge_source") == "user_pool" and "usage" in user_info:
            user_usage = user_info["usage"]
            user_limit = user_info["limit"]
            limit_msg += f"**User limit:** {user_usage['total_tokens']:,}/{user_limit:,} tokens used\n"
        elif user_info.get("charge_source") == "user_fallback" and "usage" in user_info:
            user_usage = user_info["usage"]
            user_limit = user_info["limit"]
            limit_msg += f"**User fallback limit:** {user_usage['total_tokens']:,}/{user_limit:,} tokens used\n"
        
        # Handle guild limit messages
        if guild_info.get("has_pool") and "pool_usage" in guild_info:
            pool_usage = guild_info["pool_usage"]
            pool_size = guild_info.get("pool_size", 0)
            limit_msg += f"**Guild pool:** {pool_usage['total_tokens']:,}/{pool_size:,} tokens used\n"
            
            if "member_usage" in guild_info and guild_info["member_usage"]:
                member_usage = guild_info["member_usage"]
                member_limit = guild_info.get("member_limit", 0)
                limit_msg += f"**Your guild usage:** {member_usage['total_tokens']:,}/{member_limit:,} tokens used\n"
        
        limit_msg += f"Model: **{current_model}** | Limits reset in 30 days."
        
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
            
            # Record token usage with appropriate charge source
            if token_usage_data:
                # Determine charge source based on how the request was approved
                charge_source = 'user'  # default
                if limit_info.get("user", {}).get("charge_source"):
                    charge_source = limit_info["user"]["charge_source"]
                
                token_manager.record_token_usage(token_usage_data, charge_source)
                
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
