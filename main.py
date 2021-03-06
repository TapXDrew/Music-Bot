import json
import os
import traceback

import discord
from discord.ext import commands

config = json.load(open(os.getcwd()+'/config/config.json'))

bot = commands.AutoShardedBot(command_prefix=config['Bot']['Prefix'], case_insensitive=True)
bot.remove_command('help')

bot.home_dir = os.getcwd()
bot.config = json.load(open('config/config.json'))
initial_extensions = [
                    "cogs.music_moderation",
                    "cogs.moderation",
                    "cogs.help",
                    "cogs.error",
                    "cogs.music"
                    ]

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f"Failed to load extension {extension}.")
            traceback.print_exc()
    # Optional, will need to pip-install
    bot.load_extension("jishaku")


@bot.event
async def on_message(message):
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print("------------------------------------")
    print("Bot Name: " + bot.user.name)
    print("Bot ID: " + str(bot.user.id))
    print("Discord Version: " + discord.__version__)
    print("------------------------------------")


bot.run(bot.config['Bot']['Token'])
