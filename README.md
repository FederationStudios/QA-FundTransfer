# FundTransfer Bot

## Overview
**FundTransfer Bot** is a Python-based Discord bot designed for managing group payouts in Roblox. It supports payout operations, role-based command restrictions, and provides robust error handling.

## Features
- **Group Payouts**: Effortlessly transfer Robux to members of your Roblox group.
- **Role-Based Access**: Restrict command usage to users with specific roles.
- **Enhanced Error Handling**: Detailed error messages and status updates.

## Installation

### Prerequisites
- Python 3.12+
- A Discord API Token
- A Roblox API Token
- A `.env` file for environment variables

### Setup Instructions

1. **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/FundTransfer-Bot.git
    cd FundTransfer-Bot
    ```

2. **Create and Activate a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure Environment Variables**
    Create a `.env` file in the root directory and add your environment variables:
    ```env
    DISCORD_TOKEN=your_discord_token
    ROBLOX_COOKIE=your_roblox_cookie
    GROUP_ID=your_group_id
    TWOFACTOR_SECRET=your_twofactor_secret
    ```

5. **Run the Bot**
    ```bash
    python bot.py
    ```

## Commands

- **`/grouppayout username amount`**: Payout Robux to a specified Roblox username.

## Permissions
Ensure that commands are restricted to users with appropriate roles. Modify the role names in the code to match your server’s configuration.

## Error Handling
- **Detailed Errors**: The bot provides clear error messages for command failures.
- **Rate Limits**: Handles rate limits to ensure commands respond in a timely manner.

## Contributing

1. **Fork the Repository**
2. **Create a Feature Branch**
    ```bash
    git checkout -b feature/your-feature
    ```
3. **Commit Changes**
    ```bash
    git commit -am 'Add new feature'
    ```
4. **Push to Your Branch**
    ```bash
    git push origin feature/your-feature
    ```
5. **Create a Pull Request**

## License
This project is licensed under the [MIT License](LICENSE).

## Credits
- **[discord.py](https://github.com/discordpy/discord.py)**: The library used to interact with the Discord API.
- **[Requests](https://github.com/psf/requests)**: For making HTTP requests to the Roblox API.
- **[PyOTP](https://github.com/pyauth/pyotp)**: Used for generating and validating 2FA codes.
- **[Roblox API Documentation](https://robloxsupport.zendesk.com/hc/en-us)**: For understanding the endpoints and functionality required for the bot.

## Contact
For questions or support, please reach out to [suman9725@staff.irf.red].