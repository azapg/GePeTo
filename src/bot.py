import discord
import dspy
import os
from dotenv import load_dotenv
from scrapper import log_message


load_dotenv()

# lm = dspy.LM('ollama_chat/gemma3:1b', api_base='http://localhost:11434', api_key='')
lm = dspy.LM('openai/gpt-4o-mini-2024-07-18', api_key=os.getenv('OPENAI_API_KEY'), api_base='https://api.openai.com/v1')
dspy.configure(lm=lm)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

message_history = []

# Load message history from file if it exists
try:
    with open('./data/message_history.txt', 'r', encoding="utf-8") as f:
        message_history = f.readlines()
        message_history = [msg.strip() for msg in message_history if msg.strip()]
except FileNotFoundError:
    message_history = []

@client.event
async def on_ready():
    print(f'Logged in as {client.user}!')

@client.event
async def on_message(message):
    if message.channel.id == 1377089485325729878:
        success = log_message(message)
        if success:
            print(f"Message logged: '{message.content[:50]}...'")
        return
    
    if message.author == client.user or message.author.bot:
        return
    
    message_history.append(f"{message.author.name}: {message.content}")
    
    if len(message_history) > 100:
        message_history.pop(0)        
    
    reception = discord.utils.utcnow()
    
    predict = dspy.Predict("messages: list[str] -> response")
    prediction = predict(messages=message_history)
    
    await message.reply(prediction.response)
    response_time = discord.utils.utcnow() - reception
    print(f'Response sent in {response_time.total_seconds()} seconds')
    message_history.append(f"GePeTo: {prediction.response}")
    with open('./data/message_history.txt', 'w', encoding="utf-8") as f:
        for msg in message_history:
            f.write(f"{msg}\n")
        
client.run(os.getenv('DISCORD_TOKEN'))