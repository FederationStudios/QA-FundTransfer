import discord
from discord.ext import commands
import requests
import base64
import json
import pyotp
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Set up logging
logging.basicConfig(filename='group_payout_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def has_any_role(*role_names):
    async def predicate(interaction: discord.Interaction):
        member = interaction.user
        if any(role.name in role_names for role in member.roles):
            return True
        raise discord.app_commands.MissingPermissions(missing_permissions=role_names)
    return discord.app_commands.check(predicate)

class GroupPayout(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name='grouppayout', description='Payout members in a Roblox group')
    @discord.app_commands.describe(username="Roblox username to payout", amount="Amount of Robux to payout")
    @has_any_role("Treasury Access", "Liaison")
    async def group_payout(self, interaction: discord.Interaction, username: str, amount: int):
        # Check if amount exceeds the limit
        if amount > 35:
            embed = discord.Embed(title="Group Payout", color=discord.Color.red())
            embed.add_field(name="Error", value="The payout amount cannot be greater than 35 Robux.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()  # Defer the response to avoid timeout

        embed = discord.Embed(title="Group Payout", color=discord.Color.blue())

        try:
            print("Received command, processing...")

            account_token = os.getenv('ROBLOX_COOKIE')
            group_id = os.getenv('GROUP_ID')
            twofactor_secret = os.getenv('TWOFACTOR_SECRET')
            log_channel_id = int(os.getenv('LOG_CHANNEL_ID'))  # Get the log channel ID from environment variables

            # Get user ID from username
            user_id_response = requests.get(f"https://users.roblox.com/v1/users/search?keyword={username}")
            if user_id_response.status_code != 200 or not user_id_response.json()["data"]:
                embed.add_field(name="Error", value=f"Could not find user ID for username {username}.", inline=False)
                await interaction.followup.send(embed=embed)
                return

            user_id = user_id_response.json()["data"][0]["id"]

            # Generate the 2FA code
            totp = pyotp.TOTP(twofactor_secret)
            twofactorcode = totp.now()

            full_cookie = ".ROBLOSECURITY=" + account_token
            csrf_token = requests.post("https://auth.roblox.com/v2/logout", headers={'Cookie': full_cookie}).headers['X-CSRF-TOKEN']
            payout_request_body = {
                "PayoutType": "FixedAmount",
                "Recipients": [
                    {
                        "amount": amount,
                        "recipientId": user_id,
                        "recipientType": "User"
                    }
                ]
            }

            def request_payout():
                payout_request = requests.post(
                    f"https://groups.roblox.com/v1/groups/{group_id}/payouts",
                    headers={'Cookie': full_cookie, 'X-CSRF-TOKEN': csrf_token},
                    json=payout_request_body
                )
                if payout_request.status_code == 403 and payout_request.json().get("errors", [{}])[0].get("message") == "Challenge is required to authorize the request":
                    return payout_request
                elif payout_request.status_code == 200:
                    return "Robux successfully sent!"
                else:
                    return f"payout error: {payout_request.json().get('errors', [{}])[0].get('message')} - Status Code: {payout_request.status_code} - Body: {payout_request.json()}"

            data = request_payout()
            if isinstance(data, str):
                embed.add_field(name="Status", value=data, inline=False)
                await interaction.followup.send(embed=embed)
                # Log the payout details to a specific channel
                log_channel = self.bot.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(f"Payout successful: **{username}** received **{amount} Robux** at **{interaction.created_at}**")
                return

            # Get necessary data for the 2FA validation
            challengeId = data.headers["rblx-challenge-id"]
            metadata = json.loads(base64.b64decode(data.headers["rblx-challenge-metadata"]))
            metadata_challengeId = metadata["challengeId"]
            senderId = metadata["userId"]

            # Make the actual 2FA validation
            twofactor_request_body = {
                "actionType": "Generic",
                "challengeId": metadata_challengeId,
                "code": twofactorcode
            }
            twofactor_request = requests.post(
                f"https://twostepverification.roblox.com/v1/users/{senderId}/challenges/authenticator/verify",
                headers={'Cookie': full_cookie, 'X-CSRF-TOKEN': csrf_token},
                json=twofactor_request_body
            )

            if "errors" in twofactor_request.json():
                embed.add_field(name="2FA Error", value=twofactor_request.json()['errors'][0]['message'], inline=False)
                await interaction.followup.send(embed=embed)
                return

            verification_token = twofactor_request.json()["verificationToken"]

            # Continue request for 2FA
            continue_request_body = {
                "challengeId": challengeId,
                "challengeMetadata": json.dumps({
                    "rememberDevice": False,
                    "actionType": "Generic",
                    "verificationToken": verification_token,
                    "challengeId": metadata_challengeId
                }),
                "challengeType": "twostepverification"
            }
            continue_request = requests.post(
                "https://apis.roblox.com/challenge/v1/continue",
                headers={'Cookie': full_cookie, 'X-CSRF-TOKEN': csrf_token},
                json=continue_request_body
            )

            # Final payout request
            data = request_payout()
            if isinstance(data, str):
                embed.add_field(name="Status", value=data, inline=False)
                await interaction.followup.send(embed=embed)
                # Log the payout details to a specific channel
                log_channel = self.bot.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(f"Payout successful: **{username}** received **{amount} Robux** at **{interaction.created_at}**")
            else:
                embed.add_field(name="2FA Validation", value="The 2FA validation didn't work.", inline=False)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            embed.add_field(name="Error", value=f'Failed to pay out: {e}', inline=False)
            await interaction.followup.send(embed=embed)
            logging.error(f"Failed to pay out: {e}")
            # Log the error to a specific channel
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(f"Error processing payout for **{username}**: {e}")

    @group_payout.error
    async def group_payout_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Error in group_payout command: {error}")  # Debug log
        if isinstance(error, discord.app_commands.MissingPermissions):
            missing_roles = ", ".join(error.missing_permissions)
            await interaction.followup.send(f"You do not have the required roles to use this command: {missing_roles}", ephemeral=True)
        else:
            await interaction.followup.send(f"An error occurred: {str(error)}", ephemeral=True)
        logging.error(f"Error in group_payout command: {error}")

async def setup(bot):
    await bot.add_cog(GroupPayout(bot))
