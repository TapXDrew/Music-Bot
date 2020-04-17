import json
import os
import traceback

import discord
from discord.ext import commands

config = json.load(open('config\\config.json'))
initial_extensions = ["cogs.music", "cogs.help", "cogs.error"]


class DiscordBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix="?")
        self.remove_command('help')

        self.home_dir = os.getcwd()
        self.prefix = config['bot_prefix']
        self.config = json.load(open('config\\config.json'))
        self.load_extensions()

    async def on_message(self, message):
        await self.process_commands(message)

    async def on_ready(self):
        print("------------------------------------")
        print("Bot Name: " + self.user.name)
        print("Bot ID: " + str(self.user.id))
        print("Discord Version: " + discord.__version__)
        print("------------------------------------")

    def load_extensions(self):
        for extension in initial_extensions:
            try:
                self.add_cog(extension)
            except Exception:
                print(f"Failed to load extension {extension}.")
                traceback.print_exc()
        self.add_cog("jishaku")


if __name__ == "__main__":
    bot = DiscordBot()
    bot.run(config['bot_token'])
