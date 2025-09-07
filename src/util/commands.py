import os 
import discord
from model_manager import ModelManager

async def process_commands(message: discord.Message) -> bool:
    content = message.content.strip()
    if not content.startswith('!model'):
        return False

    admin_id = os.getenv('ADMIN_ID')
    if str(message.author.id) != str(admin_id):
        return True

    # Add deprecation warning
    deprecation_msg = "⚠️ **Deprecation Notice**: Text commands are deprecated. Please use the new slash commands:\n" \
                     "• `/model` with action choices (list, current, switch, add)\n" \
                     "• Type `/model` and select an action for autocomplete and better UX!\n\n"
    
    args = content.split()
    if len(args) == 1 or (len(args) == 2 and args[1].lower() == 'list'):
        models = ModelManager.get_model_names()
        await message.channel.send(f"{deprecation_msg}Available models: {', '.join(models)}")
        return True

    if len(args) == 2 and args[1].lower() == 'current':
        await message.channel.send(f"{deprecation_msg}Current model: {ModelManager.get_current_model_name()}")
        return True

    if len(args) >= 2 and args[1].lower() == 'new':
        if len(args) < 6 or args[4] != '--provider':
            await message.channel.send(f"{deprecation_msg}Usage: !model new <model_name> <name> --provider <provider>")
            return True
        model_name = args[2]
        name = args[3]
        provider = args[5]
        if ModelManager.has_model(model_name):
            await message.channel.send(f"{deprecation_msg}Model '{model_name}' already exists. Use a different name.")
            return True
        try:
            ModelManager.add_model(model_name, name, provider=provider)
            await message.channel.send(f"{deprecation_msg}Model '{model_name}' added dynamically with provider '{provider}'.")
        except Exception as e:
            await message.channel.send(f"{deprecation_msg}Failed to add model: {e}")
        return True

    if len(args) == 2:
        model_name = args[1]
        if ModelManager.set_model(model_name):
            await message.channel.send(f"{deprecation_msg}Model switched to: {model_name}")
        else:
            await message.channel.send(f"{deprecation_msg}Unknown model: {model_name}. Use !model list to see available models.")
        return True

    await message.channel.send(f"{deprecation_msg}Usage: !model <model_name> | !model list | !model current | !model new <model_name> <name> --provider <provider>")
    return True
