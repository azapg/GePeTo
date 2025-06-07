import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from model import generate_response
from scrapper import extract_minimal_message_data
from log.message_history import add_to_message_history, get_message_history

load_dotenv()

async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    # Change to commands.Bot to support cogs
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    # Load your data logger cog
    await bot.load_extension('log.data_logger')
    
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}!')

    @bot.event
    async def on_message(message):
        if message.author == bot.user or message.author.bot or message.channel.id != int(os.getenv('TEST_CHANNEL_ID')):
            return
        
        reception = discord.utils.utcnow()
        await message.channel.typing()
        
        add_to_message_history(extract_minimal_message_data(message))
        response = generate_response(get_message_history(), message)
        
        sent = await message.reply(response, mention_author=False)
        print(f'Response sent in {discord.utils.utcnow() - reception} seconds')
        
        add_to_message_history(extract_minimal_message_data(sent))
    
    await bot.start(os.getenv('DISCORD_TOKEN'))

asyncio.run(main())