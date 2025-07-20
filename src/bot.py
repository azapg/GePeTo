import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from model import act
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
        if message.channel.id != int(os.getenv('TEST_CHANNEL_ID')):
            return
            
        print(message.mentions)
        print(bot.user)
            
        if bot.user not in message.mentions:
            return

        add_to_message_history(extract_minimal_message_data(message))
        
        if message.author == bot.user or message.author.bot:
            return
                
        reception = discord.utils.utcnow()
        
        print(f'Message {message.id} mentions GePeTo')

        async def run_agent():
            try:
                await act(get_message_history(), message)
                print(f'Acted on message: {message.content}')
                print(f'Message processed in {discord.utils.utcnow() - reception} seconds')
            except Exception as e:
                print(f'Error in agent: {e}')
                import traceback
                traceback.print_exc()
        
        asyncio.create_task(run_agent())
        
    
    await bot.start(os.getenv('DISCORD_TOKEN'))

asyncio.run(main())