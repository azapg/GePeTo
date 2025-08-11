import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from agent import act
from scrapper import extract_minimal_message_data
from bot_instance import set_bot

load_dotenv()

from util.verbosity import LOG_VERBOSITY
from util.log import _format_message_context
from util.commands import process_commands

async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    enable_data_log = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    if enable_data_log:
        await bot.load_extension('log.data_logger')
    elif LOG_VERBOSITY >= 2:
        print('Data logger disabled (DATA_LOG_MESSAGES=false)')
    
    @bot.event
    async def on_ready():
        set_bot(bot)
        print(f'Logged in as {bot.user}!')

    @bot.event
    async def on_message(message):
        if await process_commands(message):
            return

        if bot.user not in message.mentions:
            return
        if message.author == bot.user or message.author.bot:
            return

        messages = [message async for message in message.channel.history(limit=15)]
        channel_history = [extract_minimal_message_data(msg) for msg in messages]
        channel_history.reverse()
        reception = discord.utils.utcnow()

        async def run_agent():
            try:
                if LOG_VERBOSITY >= 2:
                    print(f'Acting on message {_format_message_context(message, LOG_VERBOSITY)}')
                await act(channel_history, message)
                duration_ms = int((discord.utils.utcnow() - reception).total_seconds() * 1000)
                if LOG_VERBOSITY >= 1:
                    print(f'Acted on message {_format_message_context(message, LOG_VERBOSITY)} in {duration_ms} ms')
            except Exception as e:
                if LOG_VERBOSITY >= 1:
                    print(f'Error in agent while handling {_format_message_context(message, LOG_VERBOSITY)}: {e}')
                else:
                    print(f'Error in agent: {e}')
                import traceback
                traceback.print_exc()
        
        asyncio.create_task(run_agent())
        
    
    await bot.start(os.getenv('DISCORD_TOKEN'))

asyncio.run(main())