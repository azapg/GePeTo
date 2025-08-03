import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from model import act, set_model, get_current_model_name, get_model_names
from model import ModelManager  # Import ModelManager for dynamic add
from scrapper import extract_minimal_message_data
from log.message_history import add_to_message_history, get_message_history
from bot_instance import set_bot

load_dotenv()

async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    await bot.load_extension('log.data_logger')
    
    @bot.event
    async def on_ready():
        set_bot(bot)
        print(f'Logged in as {bot.user}!')

    @bot.event
    async def on_message(message):
        if message.content.strip().startswith('!model'):
            admin_id = os.getenv('ADMIN_ID')
            if str(message.author.id) != str(admin_id):
                return
            args = message.content.strip().split()
            if len(args) == 1 or (len(args) == 2 and args[1].lower() == 'list'):
                models = get_model_names()
                await message.channel.send(f"Available models: {', '.join(models)}")
                return
            if len(args) == 2 and args[1].lower() == 'current':
                await message.channel.send(f"Current model: {get_current_model_name()}")
                return
            if len(args) >= 2 and args[1].lower() == 'new':
                if len(args) < 6 or args[4] != '--provider':
                    await message.channel.send("Usage: !model new <model_name> <name> --provider <provider>")
                    return
                model_name = args[2]
                name = args[3]
                provider = args[5]
                if ModelManager.has_model(model_name):
                    await message.channel.send(f"Model '{model_name}' already exists. Use a different name.")
                    return
                try:
                    ModelManager.add_model(model_name, name, provider=provider)
                    await message.channel.send(f"Model '{model_name}' added dynamically with provider '{provider}'.")
                except Exception as e:
                    await message.channel.send(f"Failed to add model: {e}")
                return
            if len(args) == 2:
                model_name = args[1]
                if set_model(model_name):
                    await message.channel.send(f"Model switched to: {model_name}")
                else:
                    await message.channel.send(f"Unknown model: {model_name}. Use !model list to see available models.")
                return
            await message.channel.send("Usage: !model <model_name> | !model list | !model current | !model new <model_name> <name> --provider <provider>")
            return

        if bot.user not in message.mentions:
            return
        if message.author == bot.user or message.author.bot:
            return

        messages = [message async for message in message.channel.history(limit=15)]
        channel_history = [extract_minimal_message_data(msg) for msg in messages]

        reception = discord.utils.utcnow()

        async def run_agent():
            try:
                await act(channel_history, message)
                print(f'Acted on message: {message.content}')
                print(f'Message processed in {discord.utils.utcnow() - reception} seconds')
            except Exception as e:
                print(f'Error in agent: {e}')
                import traceback
                traceback.print_exc()
        
        asyncio.create_task(run_agent())
        
    
    await bot.start(os.getenv('DISCORD_TOKEN'))

asyncio.run(main())