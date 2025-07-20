bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def get_bot():
    if bot is None:
        raise ValueError("Bot not initialized. Call set_bot() first.")
    return bot