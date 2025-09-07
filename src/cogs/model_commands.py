import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Optional
from model_manager import ModelManager


class ModelCommands(commands.Cog):
    """Discord slash commands for model management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def _is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if user is admin"""
        admin_id = os.getenv('ADMIN_ID')
        return str(interaction.user.id) == str(admin_id)
    
    async def _admin_check(self, interaction: discord.Interaction) -> bool:
        """Check admin permission and respond if not admin"""
        if not self._is_admin(interaction):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only the bot administrator can use model commands.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def model_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for model names"""
        models = ModelManager.get_model_names()
        filtered_models = [model for model in models if current.lower() in model.lower()]
        return [
            app_commands.Choice(name=model, value=model)
            for model in filtered_models[:25]  # Discord limits to 25 choices
        ]
    
    async def provider_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for provider names"""
        try:
            import json
            providers_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'providers.json')
            with open(providers_path, 'r') as f:
                providers_data = json.load(f)
            providers = list(providers_data.keys())
            filtered_providers = [provider for provider in providers if current.lower() in provider.lower()]
            return [
                app_commands.Choice(name=provider, value=provider)
                for provider in filtered_providers[:25]
            ]
        except FileNotFoundError:
            # Fallback to sample providers if providers.json doesn't exist
            fallback_providers = ["groq", "cerebras", "openai", "ollama"]
            filtered_providers = [provider for provider in fallback_providers if current.lower() in provider.lower()]
            return [
                app_commands.Choice(name=provider, value=provider)
                for provider in filtered_providers
            ]
    
    @app_commands.command(name="model", description="Model management commands")
    @app_commands.describe(
        action="Action to perform",
        model_name="Name of the model",
        display_name="Display name for the new model",
        provider="Provider for the new model"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="current", value="current"),
        app_commands.Choice(name="switch", value="switch"),
        app_commands.Choice(name="add", value="add")
    ])
    async def model_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        model_name: Optional[str] = None,
        display_name: Optional[str] = None,
        provider: Optional[str] = None
    ):
        """Main model command with subcommands"""
        if not await self._admin_check(interaction):
            return
        
        action_value = action.value
        
        if action_value == "list":
            await self._handle_list(interaction)
        elif action_value == "current":
            await self._handle_current(interaction)
        elif action_value == "switch":
            if not model_name:
                embed = discord.Embed(
                    title="❌ Missing Parameter",
                    description="Please provide a model name to switch to.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            await self._handle_switch(interaction, model_name)
        elif action_value == "add":
            if not all([model_name, display_name, provider]):
                embed = discord.Embed(
                    title="❌ Missing Parameters",
                    description="Please provide model_name, display_name, and provider to add a new model.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            await self._handle_add(interaction, model_name, display_name, provider)
    
    @model_command.autocomplete('model_name')
    async def model_name_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.model_autocomplete(interaction, current)
    
    @model_command.autocomplete('provider')
    async def provider_autocomplete_handler(self, interaction: discord.Interaction, current: str):
        return await self.provider_autocomplete(interaction, current)
    
    async def _handle_list(self, interaction: discord.Interaction):
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
                    model_list.append(f"🔹 **{model}** *(current)*")
                else:
                    model_list.append(f"🔸 {model}")
            
            embed = discord.Embed(
                title="📋 Available Models",
                description="\n".join(model_list),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Total: {len(models)} models")
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_current(self, interaction: discord.Interaction):
        """Handle current model command"""
        current_model = ModelManager.get_current_model_name()
        
        if current_model:
            embed = discord.Embed(
                title="🎯 Current Model",
                description=f"**{current_model}**",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🎯 Current Model",
                description="No model is currently selected.",
                color=discord.Color.orange()
            )
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_switch(self, interaction: discord.Interaction, model_name: str):
        """Handle model switch command"""
        if ModelManager.set_model(model_name):
            embed = discord.Embed(
                title="✅ Model Switched",
                description=f"Successfully switched to **{model_name}**",
                color=discord.Color.green()
            )
        else:
            available_models = ModelManager.get_model_names()
            embed = discord.Embed(
                title="❌ Model Not Found",
                description=f"Model `{model_name}` not found.",
                color=discord.Color.red()
            )
            if available_models:
                embed.add_field(
                    name="Available Models",
                    value=", ".join(available_models),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_add(self, interaction: discord.Interaction, model_name: str, display_name: str, provider: str):
        """Handle model add command"""
        try:
            if ModelManager.has_model(model_name):
                embed = discord.Embed(
                    title="❌ Model Exists",
                    description=f"Model `{model_name}` already exists. Please use a different name.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            ModelManager.add_model(model_name, display_name, provider=provider)
            embed = discord.Embed(
                title="✅ Model Added",
                description=f"Successfully added model **{model_name}** with provider **{provider}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Model Name", value=model_name, inline=True)
            embed.add_field(name="Display Name", value=display_name, inline=True)
            embed.add_field(name="Provider", value=provider, inline=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Add Model",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(ModelCommands(bot))