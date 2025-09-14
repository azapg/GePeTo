import asyncio
import os
import sys

from util.memory_check import validate_memory_requirements

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from agent import act
from bot_instance import set_bot
from scrapper import extract_minimal_message_data

MEMORY_EXIT_FLAG = os.getenv('MEMORY_REQUIREMENTS_EXIT', 'true').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
if not validate_memory_requirements() and MEMORY_EXIT_FLAG:
    print("Exiting due to insufficient memory.")
    print("Set MEMORY_REQUIREMENTS_EXIT=false to override this behavior.")
    sys.exit(1)

from util.verbosity import LOG_VERBOSITY
from util.log import format_message_context


async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    enable_data_log = os.getenv('DATA_LOG_MESSAGES', 'false').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    if enable_data_log:
        await bot.load_extension('log.data_logger')
    elif LOG_VERBOSITY >= 2:
        print('Data logger disabled (DATA_LOG_MESSAGES=false)')

    try:
        await bot.load_extension('cogs.model_commands')
        if LOG_VERBOSITY >= 2:
            print('Model commands cog loaded successfully')
    except Exception as e:
        print(f'Failed to load model commands cog: {e}')

    @bot.event
    async def on_ready():
        set_bot(bot)
        print(f'Logged in as {bot.user}!')

        try:
            synced = await bot.tree.sync()
            print(f'Synced {len(synced)} slash command(s)')
        except Exception as err:
            print(f'Failed to sync slash commands: {err}')

    @bot.event
    async def on_message(message):
        if message.author == bot.user or message.author.bot:
            return

        is_private = (message.guild is None)  # DMs and Group DMs
        if not is_private and bot.user not in message.mentions:
            return

        messages = [message async for message in message.channel.history(limit=15)]
        channel_history = [extract_minimal_message_data(msg) for msg in messages]
        channel_history.reverse()
        reception = discord.utils.utcnow()

        async def run_agent():
            try:
                if LOG_VERBOSITY >= 2:
                    print(f'Acting on message {format_message_context(message, LOG_VERBOSITY)}')
                await act(channel_history, message)
                duration_ms = int((discord.utils.utcnow() - reception).total_seconds() * 1000)
                if LOG_VERBOSITY >= 1:
                    print(f'Acted on message {format_message_context(message, LOG_VERBOSITY)} in {duration_ms} ms')
            except Exception as error:
                if LOG_VERBOSITY >= 1:
                    print(f'Error in agent while handling {format_message_context(message, LOG_VERBOSITY)}: {error}')
                else:
                    print(f'Error in agent: {error}')
                import traceback
                traceback.print_exc()

        asyncio.create_task(run_agent())

    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set.")

    await bot.start(token)


asyncio.run(main())
