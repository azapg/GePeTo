import discord


class ConfirmView(discord.ui.View):
    def __init__(self, initiator: int, action: str):
        super().__init__()
        self.value = None
        self.initiator = initiator
        self.action = action

    async def interaction_check(self, interaction: discord.Interaction) -> bool | None:
        if self.initiator and interaction.user.id != self.initiator:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Could we create a button for cancelling the action?
        await interaction.response.send_message(f'You confirmed the following action:\n ```{self.action}```',
                                                ephemeral=True)
        self.value = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f'This action following action was cancelled:\n ```{self.action}```',
                                                ephemeral=True)
        self.value = False
        self.stop()
