import discord
from discord.ext import commands
from discord import app_commands
from token_usage_manager import manager
from util.checks import admin_check


class TokenManagementCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="limit",
        description="Set a monthly model token limit to a specific user."
    )
    @app_commands.describe(
        user="The user to set the limit for",
        model="The model to set the limit on",
        monthly_limit="The monthly token limit"
    )
    async def set_limit(self, interaction: discord.Interaction,
                        user: discord.User, model: str, monthly_limit: int):
        if not await admin_check(interaction):
            return

        manager.set_user_limit(user.id, model, monthly_limit)
        new_limit = manager.get_user_limit(user.id, model)

        embed = discord.Embed(
            title="Monthly Token Limit Updated",
            description=f"Updated monthly token limit for {user.mention}.",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Model", value=str(model), inline=True)

        if new_limit is None:
            limit_text = "No limit set."
        else:
            if getattr(new_limit, "monthly_limit", None) == -1:
                limit_text = "Unlimited"
            else:
                limit_text = f"{new_limit.monthly_limit} tokens"

        embed.add_field(name="Monthly Limit", value=limit_text, inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="usage",
        description="Get the current month's token usage for a specific user and model."
    )
    @app_commands.describe(
        model="The model to check usage for"
    )
    async def get_usage(self, interaction: discord.Interaction, model: str):
        usage = manager.get_user_monthly_usage(interaction.user.id, model)
        limit = manager.get_user_limit(interaction.user.id, model)

        percent = None
        color = discord.Color.green()
        if limit is None:
            limit_text = "No limit set."
        else:
            monthly = getattr(limit, "monthly_limit", None)
            if monthly == -1:
                limit_text = "Unlimited"
            elif monthly is None or monthly <= 0:
                limit_text = "No limit set."
            else:
                limit_text = f"{monthly} tokens"
                percent = (usage / monthly) * 100 if monthly else 0

        embed = discord.Embed(
            title="Monthly Token Usage",
            description=f"Usage details for {interaction.user.mention} on model `{model}`",
            color=color
        )
        embed.add_field(name="Used", value=f"{usage} tokens", inline=True)
        embed.add_field(name="Limit", value=limit_text, inline=True)

        if percent is not None:
            embed.add_field(name="Usage %", value=f"{percent:.1f}", inline=True)

        await interaction.response.send_message(embed=embed)

    @get_usage.autocomplete("model")
    @set_limit.autocomplete("model")
    async def model_autocomplete(self, _, current: str):
        from util.autocomplete import model_autocomplete
        return await model_autocomplete(current)

async def setup(bot):
    await bot.add_cog(TokenManagementCommands(bot))
