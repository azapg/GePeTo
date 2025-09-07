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
        app_commands.Choice(name="📋 List Models", value="list"),
        app_commands.Choice(name="🎯 Show Current", value="current"),
        app_commands.Choice(name="🔄 Switch Model", value="switch"),
        app_commands.Choice(name="➕ Add Model", value="add")
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
                embed.add_field(
                    name="💡 Tip", 
                    value="Use autocomplete when typing the model name!", 
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            await self._handle_switch(interaction, model_name)
        elif action_value == "add":
            if not all([model_name, display_name, provider]):
                embed = discord.Embed(
                    title="❌ Missing Parameters",
                    description="Please provide all required parameters:",
                    color=discord.Color.red()
                )
                embed.add_field(name="Required", value="• **model_name**: Unique identifier\n• **display_name**: Human-readable name\n• **provider**: Service provider", inline=False)
                embed.add_field(name="💡 Tip", value="Use autocomplete for the provider field!", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            await self._handle_add(interaction, model_name, display_name, provider)
    
    @model_command.autocomplete('model_name')
    async def model_name_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.model_autocomplete(interaction, current)
    
    @model_command.autocomplete('provider')
    async def provider_autocomplete_handler(self, interaction: discord.Interaction, current: str):
        return await self.provider_autocomplete(interaction, current)
    
    @app_commands.command(name="model-info", description="Get detailed information about a specific model")
    @app_commands.describe(model_name="Name of the model to get information about")
    async def model_info_command(self, interaction: discord.Interaction, model_name: str):
        """Get detailed information about a specific model"""
        if not await self._admin_check(interaction):
            return
        
        if not ModelManager.has_model(model_name):
            embed = discord.Embed(
                title="❌ Model Not Found",
                description=f"Model `{model_name}` does not exist.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💡 Available Models", 
                value="Use `/model list` to see all available models", 
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Get model configuration details
            ModelManager._load_configurations()
            model_config = ModelManager._model_map.get(model_name, {})
            current_model = ModelManager.get_current_model_name()
            
            embed = discord.Embed(
                title=f"ℹ️ Model Information: {model_name}",
                color=discord.Color.blue()
            )
            
            # Add status indicator
            status = "🟢 Active" if model_name == current_model else "⚪ Available"
            embed.add_field(name="Status", value=status, inline=True)
            
            # Add configuration details
            if 'name' in model_config:
                embed.add_field(name="Display Name", value=f"`{model_config['name']}`", inline=True)
            
            if 'api_base' in model_config:
                # Mask sensitive parts of API base
                api_base = model_config['api_base']
                if len(api_base) > 30:
                    api_base = api_base[:15] + "..." + api_base[-10:]
                embed.add_field(name="API Endpoint", value=f"`{api_base}`", inline=False)
            
            # Add usage tip
            if model_name != current_model:
                embed.add_field(
                    name="🚀 Quick Switch", 
                    value=f"Use `/model switch {model_name}` to activate this model", 
                    inline=False
                )
            
            embed.set_footer(text=f"Model ID: {model_name}")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Retrieving Model Info",
                description="Could not retrieve model information.",
                color=discord.Color.red()
            )
            embed.add_field(name="Error", value=f"```{str(e)}```", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @model_info_command.autocomplete('model_name')
    async def model_info_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.model_autocomplete(interaction, current)
    
    @app_commands.command(name="providers", description="List available model providers")
    async def providers_command(self, interaction: discord.Interaction):
        """List all available providers and their configurations"""
        if not await self._admin_check(interaction):
            return
        
        try:
            import json
            providers_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'providers.json')
            
            with open(providers_path, 'r') as f:
                providers_data = json.load(f)
            
            if not providers_data:
                embed = discord.Embed(
                    title="📡 Available Providers",
                    description="No providers configured.",
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(
                    title="📡 Available Providers",
                    description="Configured AI model providers:",
                    color=discord.Color.blue()
                )
                
                for provider_name, config in providers_data.items():
                    api_base = config.get('api_base', 'Not specified')
                    api_key_env = config.get('api_key_env', 'Not specified')
                    
                    # Check if API key is set
                    key_status = "✅ Set" if os.getenv(api_key_env) else "❌ Missing"
                    if not api_key_env or provider_name == 'ollama':  # Ollama might not need API key
                        key_status = "➖ Not required"
                    
                    field_value = f"**Endpoint:** `{api_base}`\n**API Key:** {key_status}"
                    if api_key_env and api_key_env != '':
                        field_value += f"\n**Env Var:** `{api_key_env}`"
                    
                    embed.add_field(
                        name=f"🔌 {provider_name.title()}",
                        value=field_value,
                        inline=True
                    )
                
                embed.set_footer(text=f"Total: {len(providers_data)} providers | Use /model add to create models")
        
        except FileNotFoundError:
            embed = discord.Embed(
                title="❌ Providers Configuration Missing",
                description="The providers.json file was not found.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💡 Solution",
                value="Create a providers.json file in the project root with provider configurations.",
                inline=False
            )
        except json.JSONDecodeError:
            embed = discord.Embed(
                title="❌ Invalid Configuration",
                description="The providers.json file contains invalid JSON.",
                color=discord.Color.red()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Loading Providers",
                description="An unexpected error occurred.",
                color=discord.Color.red()
            )
            embed.add_field(name="Error Details", value=f"```{str(e)}```", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
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
                    model_list.append(f"🟢 **{model}** *(current)*")
                else:
                    model_list.append(f"🔵 {model}")
            
            embed = discord.Embed(
                title="📋 Available Models",
                description="\n".join(model_list),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Total: {len(models)} models | Use /model switch to change")
        
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
            embed.add_field(
                name="💡 Tip", 
                value="Use `/model switch` to change to a different model", 
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
                value="Use `/model list` to see available models", 
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_switch(self, interaction: discord.Interaction, model_name: str):
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
    
    async def _handle_add(self, interaction: discord.Interaction, model_name: str, display_name: str, provider: str):
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
                    value="Use `/model list` to see existing models", 
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
                value=f"Use `/model switch {model_name}` to start using this model", 
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


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(ModelCommands(bot))