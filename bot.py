import logging
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# Configure logging
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('Paying out Robux!'))
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
            except Exception as e:
                print(f'Failed to load extension {filename}: {e}')

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: Exception):
    if isinstance(error, discord.HTTPException) and error.status == 429:
        await interaction.response.send_message("Rate limit exceeded. Please try again later.", ephemeral=True)
    elif isinstance(error, commands.CommandInvokeError):
        await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have the required roles to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
    logging.error(f'Error occurred in command {interaction.data["name"]}: {error}')

bot.run(TOKEN)
