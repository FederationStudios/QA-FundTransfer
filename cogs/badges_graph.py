import discord
from discord import app_commands
from discord.ext import commands
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from io import BytesIO
import asyncio
from discord.utils import get


def has_any_role(*role_names):
    """ Custom role check decorator for Application Commands """
    async def predicate(interaction: discord.Interaction):
        member = interaction.user
        if isinstance(member, discord.Member):  # Ensure it's a member object
            for role_name in role_names:
                if get(member.roles, name=role_name):
                    return True
        raise app_commands.MissingPermissions(missing_permissions=role_names)

    return app_commands.check(predicate)


class BadgesGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_id_from_username(self, username: str) -> str:
        url = "https://users.roblox.com/v1/usernames/users"
        response = requests.post(url, json={"usernames": [username]})
        data = response.json()

        if response.status_code == 200 and data.get("data"):
            return str(data["data"][0]["id"])
        raise Exception(f"Could not find the user ID for username `{username}`.")

    async def fetch_badges(self, user_id: str):
        url = f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=100&sortOrder=Desc"
        badges = []
        cursor = None

        while True:
            params = {"cursor": cursor} if cursor else {}

            response = requests.get(url, params=params)

            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                print(f"Rate limited! Retrying after {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                continue

            data = response.json()
            badges.extend(data.get("data", []))

            if data.get("nextPageCursor"):
                cursor = data["nextPageCursor"]
            else:
                break

        return badges

    async def fetch_award_dates(self, user_id: str, badges: list):
        dates = []
        badge_ids = [badge["id"] for badge in badges]
        url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates"
        STEP = 50

        for i in range(0, len(badge_ids), STEP):
            params = {"badgeIds": badge_ids[i:i + STEP]}
            response = requests.get(url, params=params)

            # Handle rate limiting (429)
            while response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                print(f"Rate limited! Retrying after {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                response = requests.get(url, params=params)

            for badge in response.json().get("data", []):
                dates.append(badge["awardedDate"])

        return dates

    def convert_date_to_datetime(self, date: str) -> datetime:
        """ Convert Roblox API timestamps to datetime objects. """
        if '.' in date:
            date = date.split('.')[0] + 'Z'  # Truncate milliseconds for consistency
        return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")

    def plot_cumulative_badges(self, username: str, user_id: str, dates: list):
        """ Generates a cumulative badge graph as an image. """
        y_values = sorted([self.convert_date_to_datetime(date) for date in dates])

        cumulative_counts = list(range(1, len(y_values) + 1))

        plt.style.use('dark_background')
        plt.figure(figsize=(10, 5))
        plt.xlabel('Badge Earned Date')
        plt.ylabel('Total Badges')
        plt.title(f'Badges over Time for {username} ({user_id})')

        plt.scatter(y_values, cumulative_counts, marker='o', alpha=0.3)

        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())

        plt.figtext(0.05, 0.95, f"Total Badges: {len(y_values)}", ha="left", va="top", color="white", transform=ax.transAxes)

        plt.tight_layout()

        img_buf = BytesIO()
        plt.savefig(img_buf, format='png')
        img_buf.seek(0)
        plt.close()
        return img_buf

    @app_commands.command(name="badges_graph", description="Generate a badge graph for a Roblox user")
    @has_any_role("JAG Command", "QM Staff Corps", "Liaison")  # ✅ Role check applied correctly here
    async def badges_graph(self, interaction: discord.Interaction, username: str):
        """ Fetches a user's badges and generates a badge graph. """
        await interaction.response.defer()  # Prevents interaction timeout

        try:
            user_id = await self.get_user_id_from_username(username)

            # Send initial status message
            await interaction.followup.send(f"🔄 Fetching badges for `{username}`... Please wait ⏳")

            badges = await self.fetch_badges(user_id)
            dates = await self.fetch_award_dates(user_id, badges)

            if not dates:
                await interaction.followup.send(f"⚠️ No badge data found for `{username}`.")
                return

            img_buf = self.plot_cumulative_badges(username, user_id, dates)

            file = discord.File(img_buf, filename="badges_graph.png")
            await interaction.followup.send(f"📊 Here is the badge graph for `{username}`:", file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: `{e}`")
    
    @badges_graph.error
    async def badges_graph_error(self, interaction: discord.Interaction, error: Exception):
        """ Handles permission errors for `/badges_graph` """
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("🚫 You do not have the required roles to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ An unexpected error occurred.", ephemeral=True)
        print(f'Error in command /badges_graph: {error}')

async def setup(bot):
    await bot.add_cog(BadgesGraph(bot))
