"""Model operations utility functions for Discord interactions"""

import discord
from model_manager import ModelManager


async def handle_list(interaction: discord.Interaction):
    """Handle model list command"""
    models = ModelManager.get_model_names()
    current_model = ModelManager.get_current_model_name()
    
    if not models:
        embed = discord.Embed(
            title="📋 Available Models",
            description="No models configured.",
            color=discord.Color.orange()
        )
    else:
        model_list = []
        for model in models:
            if model == current_model:
                model_list.append(f"🟢 **{model}** *(current)*")
            else:
                model_list.append(f"🔵 {model}")
        
        embed = discord.Embed(
            title="📋 Available Models",
            description="\n".join(model_list),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total: {len(models)} models | Use /model-switch to change")
    
    await interaction.response.send_message(embed=embed)


async def handle_current(interaction: discord.Interaction):
    """Handle current model command"""
    current_model = ModelManager.get_current_model_name()
    
    if current_model:
        embed = discord.Embed(
            title="🎯 Current Model",
            description=f"**{current_model}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="💡 Tip", 
            value="Use `/model-switch` to change to a different model", 
            inline=False
        )
    else:
        embed = discord.Embed(
            title="🎯 Current Model",
            description="No model is currently selected.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="💡 Next Steps", 
            value="Use `/model-list` to see available models", 
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)


async def handle_switch(interaction: discord.Interaction, model_name: str):
    """Handle model switch command"""
    if ModelManager.set_model(model_name):
        embed = discord.Embed(
            title="✅ Model Switched Successfully",
            description=f"Now using **{model_name}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🔄 Status", 
            value="All future AI responses will use this model", 
            inline=False
        )
        embed.set_footer(text="Changes take effect immediately")
    else:
        available_models = ModelManager.get_model_names()
        embed = discord.Embed(
            title="❌ Model Not Found",
            description=f"Model `{model_name}` not found.",
            color=discord.Color.red()
        )
        if available_models:
            models_text = "\n".join([f"• {model}" for model in available_models])
            embed.add_field(
                name="📋 Available Models",
                value=models_text,
                inline=False
            )
        embed.set_footer(text="Use autocomplete when typing the model name!")
    
    await interaction.response.send_message(embed=embed)


async def handle_add(interaction: discord.Interaction, model_name: str, display_name: str, provider: str):
    """Handle model add command"""
    try:
        if ModelManager.has_model(model_name):
            embed = discord.Embed(
                title="❌ Model Already Exists",
                description=f"Model `{model_name}` already exists. Please use a different name.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💡 Tip", 
                value="Use `/model-list` to see existing models", 
                inline=False
            )
            await interaction.response.send_message(embed=embed)
            return
        
        ModelManager.add_model(model_name, display_name, provider=provider)
        embed = discord.Embed(
            title="✅ Model Added Successfully",
            description=f"**{model_name}** is now available for use!",
            color=discord.Color.green()
        )
        embed.add_field(name="🏷️ Model Name", value=f"`{model_name}`", inline=True)
        embed.add_field(name="📛 Display Name", value=f"`{display_name}`", inline=True)
        embed.add_field(name="🔌 Provider", value=f"`{provider}`", inline=True)
        embed.add_field(
            name="🚀 Next Steps", 
            value=f"Use `/model-switch {model_name}` to start using this model", 
            inline=False
        )
        embed.set_footer(text="Model configuration saved dynamically")
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Failed to Add Model",
            description=f"An error occurred while adding the model.",
            color=discord.Color.red()
        )
        embed.add_field(name="🐛 Error Details", value=f"```{str(e)}```", inline=False)
        
        # Provide helpful troubleshooting tips
        if "API key" in str(e).lower():
            embed.add_field(
                name="💡 Troubleshooting", 
                value="Make sure the required API key environment variable is set", 
                inline=False
            )
        elif "provider" in str(e).lower():
            embed.add_field(
                name="💡 Available Providers", 
                value="Use autocomplete to see valid provider options", 
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)