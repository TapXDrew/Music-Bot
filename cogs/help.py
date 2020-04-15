import discord
from discord.ext import commands


class Help(commands.Cog):
    """
    Command file to be loaded into a discord bot
    """
    def __init__(self, bot):
        """
        Initializes the bot
        :param bot: discord.Bot
        """
        self.bot = bot  # Lets us use the bot in various other parts of the bot to access information like the voice state of the bot

    @commands.command(name='Help', help="The command you are looking at")
    async def help(self, ctx, command=None):
        """
        Help command shows all other commands
        :param ctx: Information on the context of where the command was called
        :param command: Shows a more detailed explanation of the command and how to use it
        """
        if not command:
            embed = discord.Embed(title='Help', color=discord.Color.green())
            for command in self.bot.commands:
                if command.name in ['jishaku', 'help']:
                    continue
                embed.add_field(name=command.qualified_name, value=command.help, inline=False)
            await ctx.send(embed=embed)
        else:
            pass


def setup(bot):
    bot.add_cog(Help(bot))
