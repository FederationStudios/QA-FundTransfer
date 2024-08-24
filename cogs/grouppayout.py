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

            headers = {'Cookie': f".ROBLOSECURITY={account_token}"}

            # Function to set CSRF token
            def set_csrf():
                request = requests.post("https://auth.roblox.com/v2/logout", headers=headers)
                if request.status_code == 401:
                    raise ValueError("Incorrect roblosecurity cookie")
                headers.update({'X-CSRF-TOKEN': request.headers['X-CSRF-TOKEN']})

            # Function to send payout request
            def payout_request():
                request = requests.post(f"https://groups.roblox.com/v1/groups/{group_id}/payouts", headers=headers, json={
                    "PayoutType": "FixedAmount",
                    "Recipients": [
                        {
                            "amount": amount,
                            "recipientId": user_id,
                            "recipientType": "User"
                        }
                    ]
                })
                if request.status_code == 403 and request.json().get("errors", [{}])[0].get("message") == "Challenge is required to authorize the request":
                    return request
                elif request.status_code == 200:
                    return "Robux successfully sent!"
                else:
                    raise ValueError(f"Payout error: {request.json().get('errors', [{}])[0].get('message')} - Status Code: {request.status_code}")

            # Function to verify 2FA request
            def verify_request(senderId, metadata_challengeId):
                totp = pyotp.TOTP(twofactor_secret)
                code = totp.now()
                request = requests.post(f"https://twostepverification.roblox.com/v1/users/{senderId}/challenges/authenticator/verify", headers=headers, json={
                    "actionType": "Generic",
                    "challengeId": metadata_challengeId,
                    "code": code
                })
                if "errors" in request.json():
                    raise ValueError(f"2FA error: {request.json()['errors'][0]['message']}")
                return request.json()["verificationToken"]

            # Function to continue 2FA request
            def continue_request(challengeId, verification_token, metadata_challengeId):
                requests.post("https://apis.roblox.com/challenge/v1/continue", headers=headers, json={
                    "challengeId": challengeId,
                    "challengeMetadata": json.dumps({
                        "rememberDevice": False,
                        "actionType": "Generic",
                        "verificationToken": verification_token,
                        "challengeId": metadata_challengeId
                    }),
                    "challengeType": "twostepverification"
                })

            # Step-by-step process for payout
            set_csrf()
            data = payout_request()
            if isinstance(data, str):
                embed.add_field(name="Status", value=data, inline=False)
                await interaction.followup.send(embed=embed)
                log_channel = self.bot.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(f"Payout successful: **{username}** received **{amount} Robux** at **{interaction.created_at}**")
                return

            # 2FA Challenge Handling
            challengeId = data.headers["rblx-challenge-id"]
            metadata = json.loads(base64.b64decode(data.headers["rblx-challenge-metadata"]))
            metadata_challengeId = metadata["challengeId"]
            senderId = metadata["userId"]

            # Verify 2FA and Continue Request
            verification_token = verify_request(senderId, metadata_challengeId)
            continue_request(challengeId, verification_token, metadata_challengeId)

            # Update headers for final payout request
            headers.update({
                'rblx-challenge-id': challengeId,
                'rblx-challenge-metadata': base64.b64encode(json.dumps({
                    "rememberDevice": False,
                    "actionType": "Generic",
                    "verificationToken": verification_token,
                    "challengeId": metadata_challengeId
                }).encode()).decode(),
                'rblx-challenge-type': "twostepverification"
            })

            # Final payout request
            data = payout_request()
            embed.add_field(name="Status", value=data if isinstance(data, str) else "The 2FA validation didn't work.", inline=False)
            await interaction.followup.send(embed=embed)
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(f"Payout successful: **{username}** received **{amount} Robux** at **{interaction.created_at}**")

        except Exception as e:
            embed.add_field(name="Error", value=f'Failed to pay out: {e}', inline=False)
            await interaction.followup.send(embed=embed)
            logging.error(f"Failed to pay out: {e}")
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
