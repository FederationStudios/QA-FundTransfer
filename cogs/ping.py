from discord.ext import commands
from discord import app_commands, Interaction
from discord.utils import get

def has_any_role(*role_names):
    async def predicate(interaction: Interaction):
        member = interaction.user
        for role_name in role_names:
            role = get(member.roles, name=role_name)
            if role:
                return True
        raise app_commands.MissingPermissions(missing_permissions=role_names)
    return app_commands.check(predicate)

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    @has_any_role("Quartermaster Staff")  # Replace with the names of the roles you want to check
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message(f"Pong! Latency is {self.bot.latency * 1000:.2f}ms")

    @ping.error
    async def ping_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You do not have the required roles to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
        print(f'Error in command ping: {error}')

async def setup(bot):
    await bot.add_cog(PingCog(bot))
