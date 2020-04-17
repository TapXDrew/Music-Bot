import asyncio
import json
import os
import traceback

import discord
from discord.ext import commands

config = json.load(open('config\\config.json'))
initial_extensions = [
            "cogs.music",  # All music related commands
            "cogs.help",  # The help command
            "cogs.error"  # Error catcher
        ]


class Bot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(config['bot_prefix']), description="A simple music bot in Discord.PY")

        self.home_dir = os.getcwd()
        self.config = json.load(open('config\\config.json'))

        self.remove_command('help')

    async def on_ready(self):
        print("------------------------------------")
        print("Bot Name: " + self.user.name)
        print("Bot ID: " + str(self.user.id))
        print("Discord Version: " + discord.__version__)
        print("------------------------------------")

    def load_commands(self, cogs):
        for extension in cogs:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension {extension}.")
                traceback.print_exc()
        # Optional, will need to pip-install
        self.load_extension("jishaku")


async def run():
    bot = Bot()
    bot.load_commands(initial_extensions)
    await bot.start(config['bot_token'])


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
