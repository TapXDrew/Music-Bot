import json
import time

import discord
from discord.ext import commands

from utils.moderation import User

config = json.load(open('../config/config.json'))


class Moderation(commands.Cog):
    def __init__(self, bot):
        year, month, day, hour, min = map(int, time.strftime("%Y %m %d %H %M").split())
        self.bot = bot
        self.date = f"{year}-{month}-{day}"

        self.FailModeration = int(config["Embeds Colors"]["Fail Moderation"], 16)
        self.SuccessModeration = int(config["Embeds Colors"]["Success Moderation"], 16)

    @commands.command()
    async def history(self, ctx, member: discord.Member):
        Info = User(self.bot, ctx, member)
        await ctx.send(Info.history)

    @commands.command()
    async def kick(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        kicked_members = []
        failed_members = []
        for member in members:
            kickingInfo = User(self.bot, ctx, member)
            try:
                await ctx.guild.kick(member, reason=reason)
                kicked_members.append(member.name)
                kickingInfo.add_history(event="Kicked", reason=reason, moderator=ctx.author, date=self.date)
            except discord.errors.Forbidden:
                failed_members.append(member.name)
        embed = discord.Embed(title="Kicked", color=self.SuccessModeration)
        if kicked_members:
            embed.add_field(name="Members Kicked", value='\n'.join(kicked_members))
        if failed_members:
            embed.add_field(name="Failed to kick", value='\n'.join(failed_members))
        await ctx.send(embed=embed)

    @commands.command()
    async def softban(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        print(members, reason)
        banned_members = []
        failed_members = []
        for member in members:
            banningInfo = User(self.bot, ctx, member)
            await ctx.guild.ban(member, reason=reason)
            banned_members.append(member.name)
            banningInfo.add_history(event="Soft-Banned", reason=reason, moderator=ctx.author, date=self.date)
            await ctx.guild.unban(member)
        embed = discord.Embed(title="Soft-Banned", color=self.SuccessModeration)
        if banned_members:
            embed.add_field(name="Members Soft-Banned", value='\n'.join(banned_members))
        if failed_members:
            embed.add_field(name="Failed to Soft-Banned", value='\n'.join(failed_members))
        await ctx.send(embed=embed)

    @commands.command()
    async def ban(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        banned_members = []
        failed_members = []
        for member in members:
            banningInfo = User(self.bot, ctx, member)
            try:
                await ctx.guild.ban(member, reason=reason)
                banned_members.append(member.name)
                banningInfo.add_history(event="Banned", reason=reason, moderator=ctx.author, date=self.date)
            except Exception:
                failed_members.append(member.name)
        embed = discord.Embed(title="Banned", color=self.SuccessModeration)
        if banned_members:
            embed.add_field(name="Members Banned", value='\n'.join(banned_members))
        if failed_members:
            embed.add_field(name="Failed to ban", value='\n'.join(failed_members))
        await ctx.send(embed=embed)

    @commands.command()
    async def unban(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        unbanned_members = []
        failed_members = []
        for member in members:
            banningInfo = User(self.bot, ctx, member)
            try:
                await ctx.guild.unban(member, reason=reason)
                unbanned_members.append(member.name)
                banningInfo.add_history(event="Un-Banned", reason=reason, moderator=ctx.author, date=self.date)
            except Exception:
                failed_members.append(member.name)
        embed = discord.Embed(title="Un-Banned", color=self.SuccessModeration)
        if unbanned_members:
            embed.add_field(name="Members Un-Banned", value='\n'.join(unbanned_members))
        if failed_members:
            embed.add_field(name="Failed to un-ban", value='\n'.join(failed_members))
        await ctx.send(embed=embed)

    @commands.command()
    async def tempmute(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def mute(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def unmute(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def warn(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def unwarn(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def warnings(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def purge(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass

    @commands.command()
    async def slowmode(self, ctx, members: commands.Greedy[discord.Member], *, reason='No Reason Provided'):
        pass


def setup(bot):
    bot.add_cog(Moderation(bot))
