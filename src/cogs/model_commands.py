import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Optional
from model_manager import ModelManager
from token_manager import get_token_manager
from util.model_operations import handle_list, handle_current, handle_switch, handle_add


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
            # Return empty list if providers.json doesn't exist
            return []
    
    @app_commands.command(name="model-list", description="📋 List all available models")
    async def model_list_command(self, interaction: discord.Interaction):
        """List all available models"""
        if not await self._admin_check(interaction):
            return
        await handle_list(interaction)
    
    @app_commands.command(name="model-current", description="🎯 Show the currently active model")
    async def model_current_command(self, interaction: discord.Interaction):
        """Show current model"""
        if not await self._admin_check(interaction):
            return
        await handle_current(interaction)
    
    @app_commands.command(name="model-switch", description="🔄 Switch to a different model")
    @app_commands.describe(model_name="Name of the model to switch to")
    async def model_switch_command(self, interaction: discord.Interaction, model_name: str):
        """Switch to a different model"""
        if not await self._admin_check(interaction):
            return
        await handle_switch(interaction, model_name)
    
    @model_switch_command.autocomplete('model_name')
    async def model_switch_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.model_autocomplete(interaction, current)
    
    @app_commands.command(name="model-add", description="➕ Add a new model dynamically")
    @app_commands.describe(
        model_name="Unique identifier for the model",
        display_name="Human-readable display name",
        provider="Provider service (e.g., openai, groq)"
    )
    async def model_add_command(
        self, 
        interaction: discord.Interaction, 
        model_name: str, 
        display_name: str, 
        provider: str
    ):
        """Add a new model"""
        if not await self._admin_check(interaction):
            return
        await handle_add(interaction, model_name, display_name, provider)
    
    @model_add_command.autocomplete('provider')
    async def model_add_provider_autocomplete(self, interaction: discord.Interaction, current: str):
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
                value="Use `/model-list` to see all available models", 
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
                    value=f"Use `/model-switch {model_name}` to activate this model", 
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
                
                embed.set_footer(text=f"Total: {len(providers_data)} providers | Use /model-add to create models")
        
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
    
    @app_commands.command(name="token-usage", description="🪙 Check your token usage")
    async def token_usage_command(self, interaction: discord.Interaction):
        """Check token usage for user and guild"""
        token_manager = get_token_manager()
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Get usage data
        user_usage = token_manager.get_user_usage(user_id)
        guild_usage = token_manager.get_guild_usage(guild_id) if guild_id else None
        
        # Check limits
        user_ok, user_info = token_manager.check_user_limit(user_id)
        guild_ok, guild_info = token_manager.check_guild_limit(guild_id)
        
        embed = discord.Embed(
            title="🪙 Token Usage",
            color=discord.Color.blue()
        )
        
        # User usage
        user_status = "✅" if user_ok else "❌"
        user_text = f"{user_status} **{user_usage['total_tokens']:,}** tokens used"
        
        if "limit" in user_info:
            remaining = user_info.get("remaining", 0)
            limit = user_info["limit"]
            percentage = (user_usage['total_tokens'] / limit) * 100 if limit > 0 else 0
            user_text += f" / **{limit:,}** ({percentage:.1f}%)"
            user_text += f"\n🔄 **{remaining:,}** tokens remaining"
        elif user_info.get("bypass"):
            user_text += " (unlimited access)"
        else:
            user_text += " (no limits configured)"
        
        user_text += f"\n📊 **{user_usage['call_count']}** calls in last {user_usage['timeframe_days']} days"
        
        embed.add_field(
            name="👤 Your Usage",
            value=user_text,
            inline=False
        )
        
        # Guild usage (if applicable)
        if guild_usage and guild_id:
            guild_status = "✅" if guild_ok else "❌"
            guild_text = f"{guild_status} **{guild_usage['total_tokens']:,}** tokens used"
            
            if "limit" in guild_info:
                remaining = guild_info.get("remaining", 0)
                limit = guild_info["limit"]
                percentage = (guild_usage['total_tokens'] / limit) * 100 if limit > 0 else 0
                guild_text += f" / **{limit:,}** ({percentage:.1f}%)"
                guild_text += f"\n🔄 **{remaining:,}** tokens remaining"
            elif guild_info.get("bypass"):
                guild_text += " (unlimited access)"
            else:
                guild_text += " (no limits configured)"
            
            guild_text += f"\n📊 **{guild_usage['call_count']}** calls by **{guild_usage['unique_users']}** users"
            
            embed.add_field(
                name="🏠 Server Usage",
                value=guild_text,
                inline=False
            )
        
        # Breakdown
        if user_usage['total_tokens'] > 0:
            breakdown = f"📝 **{user_usage['prompt_tokens']:,}** prompt tokens\n"
            breakdown += f"🤖 **{user_usage['completion_tokens']:,}** completion tokens"
            embed.add_field(
                name="📈 Breakdown",
                value=breakdown,
                inline=True
            )
        
        if not user_ok or (guild_id and not guild_ok):
            embed.add_field(
                name="⚠️ Limit Exceeded",
                value="You cannot use the bot until limits reset or are increased.",
                inline=False
            )
        
        embed.set_footer(text="Token usage resets monthly • Contact admin for limit increases")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="token-stats", description="📊 View overall token statistics (Admin only)")
    async def token_stats_command(self, interaction: discord.Interaction):
        """View overall token usage statistics"""
        if not await self._admin_check(interaction):
            return
        
        token_manager = get_token_manager()
        stats = token_manager.get_usage_statistics()
        
        embed = discord.Embed(
            title="📊 Token Usage Statistics",
            description=f"Last {stats['timeframe_days']} days",
            color=discord.Color.gold()
        )
        
        overall = stats['overall']
        
        # Overall stats
        overall_text = f"🪙 **{overall['total_tokens'] or 0:,}** total tokens\n"
        overall_text += f"📝 **{overall['total_prompt'] or 0:,}** prompt tokens\n"
        overall_text += f"🤖 **{overall['total_completion'] or 0:,}** completion tokens\n"
        overall_text += f"📞 **{overall['total_calls'] or 0:,}** API calls\n"
        overall_text += f"👥 **{overall['unique_users'] or 0}** active users\n"
        overall_text += f"🏠 **{overall['unique_guilds'] or 0}** active servers\n"
        overall_text += f"🎯 **{overall['unique_sessions'] or 0}** chat sessions"
        
        embed.add_field(
            name="🌍 Overall Usage",
            value=overall_text,
            inline=False
        )
        
        # Top users
        if stats['top_users']:
            top_users_text = ""
            for i, user in enumerate(stats['top_users'][:5], 1):
                top_users_text += f"{i}. <@{user['user_id']}>: **{user['total_tokens']:,}** tokens\n"
            embed.add_field(
                name="🏆 Top Users",
                value=top_users_text,
                inline=True
            )
        
        # Top servers
        if stats['top_guilds']:
            top_guilds_text = ""
            for i, guild in enumerate(stats['top_guilds'][:5], 1):
                top_guilds_text += f"{i}. Server {guild['guild_id']}: **{guild['total_tokens']:,}** tokens\n"
            embed.add_field(
                name="🏆 Top Servers",
                value=top_guilds_text,
                inline=True
            )
        
        # Model usage
        if stats['model_usage']:
            model_text = ""
            for model in stats['model_usage'][:3]:
                avg_tokens = model['avg_tokens_per_call'] or 0
                model_text += f"🤖 **{model['model']}**: {model['total_tokens']:,} tokens ({avg_tokens:.0f} avg/call)\n"
            embed.add_field(
                name="🔧 Model Usage",
                value=model_text,
                inline=False
            )
        
        embed.set_footer(text="Statistics are calculated from recorded usage data")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(ModelCommands(bot))