import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Load cogs
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def main():
    await load_extensions()
    await bot.start(os.getenv('DISCORD_TOKEN'))

asyncio.run(main())


# @bot.event
# async def on_application_command_error(interaction: discord.Interaction, error: Exception):
#     if isinstance(error, discord.HTTPException) and error.status == 429:
#         await interaction.response.send_message("Rate limit exceeded. Please try again later.", ephemeral=True)
#     elif isinstance(error, commands.CommandInvokeError):
#         await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)
#     elif isinstance(error, discord.app_commands.MissingPermissions):
#         await interaction.response.send_message("You do not have the required roles to use this command.", ephemeral=True)
#     else:
#         await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
#     logging.error(f'Error occurred in command {interaction.data["name"]}: {error}')

# bot.run(TOKEN)
