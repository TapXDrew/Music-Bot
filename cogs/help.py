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

    @commands.command(name='Help', help="The command you are looking at", usage="!help [command]")
    async def help(self, ctx, search_command=None):
        """
        Help command shows all other commands
        :param ctx: Information on the context of where the command was called
        :param search_command: Shows a more detailed explanation of the command and how to use it
        """
        if not search_command:
            embed = discord.Embed(title='Help', color=discord.Color.green())
            for command in self.bot.commands:
                if command.name in ['jishaku', 'Help'] or command.hidden:
                    continue
                embed.add_field(name=command.qualified_name, value=command.help, inline=False)
            await ctx.send(embed=embed)
        else:
            for command in self.bot.commands:
                if command.name.lower() == search_command.lower() or search_command.lower() in [aliases.lower() for aliases in command.aliases]:
                    embed = discord.Embed(title=command.name, color=discord.Color.green())
                    embed.add_field(name="Prefix", value=self.bot.command_prefix, inline=False)
                    embed.add_field(name="Help", value=command.help, inline=False)
                    embed.add_field(name="Usage", value=self.bot.command_prefix+command.usage, inline=False)
                    embed.add_field(name="Aliases", value=', '.join(command.aliases), inline=False)
                    return await ctx.send(embed=embed)
            await ctx.send("Sorry but I could not find that command!")


def setup(bot):
    bot.add_cog(Help(bot))
