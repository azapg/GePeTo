import os

import discord


def is_admin(interaction: discord.Interaction) -> bool:
    admin_id = os.getenv('ADMIN_ID')
    return str(interaction.user.id) == str(admin_id)


async def admin_check(interaction: discord.Interaction) -> bool:
    if not is_admin(interaction):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the bot administrator can use model commands.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return True
