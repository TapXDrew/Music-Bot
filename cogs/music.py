import asyncio
import math
import os
import random
import re
import urllib.parse
import urllib.request

import discord
import youtube_dl
from discord.ext import commands
from path import Path

from utils.user import User
from utils.queues import SavedQueues

# Changing our current working directory so downloads will download to an audio folder
Path(os.getcwd()+"/audio_cache").cd()


class Queue:
    """
    Queue
    -----
    Create an object containing the next song to be streamed in discord
    """
    def __init__(self):
        """
        Initializes the queue list
        """
        self.queue = list()
        self.repeat = False

    def put(self, item, place=0):
        """
        Inserts an item the index 0 of self.queue
        """
        self.queue.insert(place, item)
        return True

    def get(self):
        """
        Gets the last item in the list so that it is grabbing the next item to be played and removes it from the list
        -----
        Returns the song to be played if any, otherwise returns False
        """
        if len(self.queue) > 0:
            removed = self.queue.pop()
            return removed
        return False

    def list_queue(self):
        """
        Returns information on the current queue
        """
        return self.queue

    def next_up(self):
        """
        Returns the next song in the queue
        """
        if len(self.queue) > 0:
            return self.queue[-1].title
        return None

    def just_added(self):
        """
        Returns the newest song in the queue
        """
        if len(self.queue) > 0:
            return self.queue[0].title
        return None

    def remove(self, place):
        """
        Removes an item from the queue based on the index
        """
        if len(self.queue) >= place:
            return self.queue.pop(place - 1)
        return False

    def find(self, place):
        """
        Finds an item from the queue based on the index
        """
        if len(self.queue) >= place:
            return self.queue[place-1]
        return False


class AudioSourcePlayer(discord.PCMVolumeTransformer):  # This is our video download/player so we can send a stream of audio to a Voice Channel
    def __init__(self, source, *, data):
        super().__init__(source, 0.5)

        self.data = data

        self.url = data.get('url')
        self.artist = data.get('artist')
        self.title = data.get('title')

        self.requester = data.get('requester')
        self.ctx = data.get('ctx')
        self.repeat = False
        self.stop_all = False

    @classmethod
    async def download(cls, url, *, loop=None, stream=False, ctx):
        youtube_dl.utils.bug_reports_message = lambda: ''
        ffmpeg_options = {'options': '-vn'}
        ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s', 'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto', 'source_address': '0.0.0.0'}
        ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        data["ctx"] = ctx if ctx else "No Additional Information"  # Stores the context of the song
        data['requester'] = ctx.author if ctx else "Auto-Play"  # Store the song requester

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, executable="C:/ffmpeg/bin/ffmpeg.exe", **ffmpeg_options), data=data)


class Music(commands.Cog):
    """
    Command file to be loaded into a discord bot
    """
    def __init__(self, bot):
        """
        Initializes the bot to be used for music
        :param bot: discord.Bot
        """
        self.user = None  # This lets us check music permissions for a giver user
        self.bot = bot  # Lets us use the bot in various other parts of the bot to access information like the voice state of the bot
        self.players = {}  # Each servers' music player is stored here so we can get information on the current song, pause, play, ect while being server exclusive
        self.queues = {}  # Each servers' Queue object is stored here

    def cog_check(self, ctx):
        self.user = User(bot=self.bot, ctx=ctx)
        return True

    # Extra Functions
    @staticmethod
    def get_song(song):
        """
        Gets a video link from youtube based on the param song
        :param song: A song name or title to search on youtube and return a video ID
        -----
        If no video is found then return False, otherwise return the video ID
        """
        query_string = urllib.parse.urlencode({"search_query": song})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        search_results = re.findall(r'href=\"/watch\?v=(.{11})', html_content.read().decode())
        try:
            return search_results[0]
        except IndexError:
            return False

    async def play_next_song(self, ctx, queue_type='Player'):
        """
        Plays the next queued song if the bot is not already playing a song in the server
        :param ctx: Information on the context of where the command was called
        :param queue_type: How the command was called
        """
        queue = self.queues[ctx.guild.id]  # Gets the current servers queue
        player = self.players[ctx.guild.id]  # Current player for the guild
        if ctx.message.guild.voice_client.is_playing() or ctx.message.guild.voice_client.is_paused() and queue_type == 'Player':  # Checking if we send a message saying that the song is queued or will now play
            embed = discord.Embed(color=discord.Color.green())
            embed.add_field(name=f"Song added to the queue", value=f"{queue.just_added()} has been added to the queue")
            embed.set_footer(text=f"Queue Length: {len(queue.queue)}")
            await ctx.send(embed=embed)
        while True:
            await asyncio.sleep(2)
            if ctx.message.guild.voice_client and ctx.message.guild.voice_client.is_playing() or ctx.message.guild.voice_client and ctx.message.guild.voice_client.is_paused():  # If the bot is currently playing a song or has a paused song, then we wait 5 seconds then check again
                await asyncio.sleep(3)
                continue
            else:
                if player and player.stop_all:
                    return
                elif player and player.repeat:
                    result = self.get_song(player.title)  # Gets a video ID for the song
                    player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player
                elif queue.repeat:
                    result = self.get_song(player.title)  # Gets a video ID for the song
                    player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player
                    queue.put(player)
                    player = queue.get()
                else:
                    player = queue.get()  # Gets the next song to play on the server
                if not player:  # If there is no next song, we auto play music
                    with open('..\\config\\_autoplaylist.txt', 'r+') as playlist:
                        songs = [song.strip() for song in playlist.readlines()]
                    ctx.author = None
                    await self.stream(ctx=ctx, url=random.choice(songs), queue_type='Auto')
                    return
                else:  # There is still a song on queue so we will now play it
                    self.players[ctx.guild.id] = player  # Either adds the player to the dict using the server ID or updates the current player
                    ctx.guild.voice_client.play(player)  # Plays audio in the voice chat
                    embed = discord.Embed(color=discord.Color.green())
                    embed.add_field(name=f"{player.title} is now playing!", value=f"Next Up: {queue.next_up()}")
                    embed.set_footer(text=f"Queue Length: {len(queue.queue)}")
                    await ctx.send(embed=embed)
            continue

    async def start_vote(self, vote_type, player, ctx):
        reactions = {}
        vote = 1
        if vote_type == "Skip":
            embed = discord.Embed(title=f"Vote Skip started", color=discord.Color.orange())
            embed.add_field(name="React with :thumbsup: to skip the song, :thumbsdown: to continue", value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the song will NOT be skipped")
            message = await ctx.send(embed=embed)
        elif vote_type == "Queue Remove":
            embed = discord.Embed(title=f"Vote to remove an item from queue", color=discord.Color.orange())
            embed.add_field(name=f"React with :thumbsup: to remove `{player.title}`, :thumbsdown: to continue", value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the song will NOT be removed")
            message = await ctx.send(embed=embed)
        elif vote_type == "Queue Clear":
            embed = discord.Embed(title=f"Vote to clear the queue", color=discord.Color.orange())
            embed.add_field(name=f"React with :thumbsup: to remove `{player.title}`, :thumbsdown: to continue", value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the queue will NOT be cleared")
            message = await ctx.send(embed=embed)
        elif vote_type == "Stop":
            embed = discord.Embed(title=f"Vote to stop all music", color=discord.Color.orange())
            embed.add_field(name=f"React with :thumbsup: to stop the music, :thumbsdown: to continue listening", value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the music will continue")
            message = await ctx.send(embed=embed)
        else:
            return False
        for emote in ["👍", "👎"]:
            await message.add_reaction(emote)
        for _ in range(30):
            try:
                react, user = await self.bot.wait_for('reaction_add', timeout=1)
                if react.emoji == "👍":
                    reactions[user.id] = True
                elif react.emoji == "👎":
                    reactions[user.id] = False
            except Exception:
                continue
        for user, react in reactions.items():
            if user == ctx.author.id or user == self.bot.user:
                continue
            elif react:
                vote += 1
            else:
                vote -= 1
        if vote >= 0:
            return True
        return False

    # Commands
    @commands.command(name='Join', aliases=['summon'])
    async def join(self, ctx, channel: discord.VoiceChannel = None):
        """
        Joins the voice channel that the author is in or, if specified, joins the channel specified in the channel param
        :param ctx: Information on the context of where the command was called
        :param channel: If a channel is specified then we will join it, otherwise we join the current voice channel the message author is in, if any
        """
        if ctx.author.voice:
            if ctx.guild.voice_client:  # Checks if the bot is already in a voice channel, if so we leave it
                await self.leave()
            return await ctx.author.voice.channel.connect()  # Joins the VC that the command author is in
        elif channel:
            return await channel.connect()
        else:
            embed = discord.Embed(title="Failed to join a voice channel", color=discord.Color.red())
            embed.add_field(name="I cant play music if i cant talk!", value="Please join a voice channel before trying to play music!")
            await ctx.send(embed=embed)

    @commands.command(name='Leave')
    async def leave(self, ctx):
        """
        Leaves the current voice channel if the bot is in one
        :param ctx: Information on the context of where the command was called
        """
        if ctx.guild.voice_client:  # Checks if the bot is already in a voice channel, if so we leave it
            await ctx.guild.voice_client.disconnect()

    @commands.command(name='Play', aliases=['p', 'Song', 'Sing'])
    async def play(self, ctx, *, song=None, queue_type='Player'):
        """
        Adds the specified song to the queue to be played
        :param ctx: Information on the context of where the command was called
        :param song: The song to be queued
        :param queue_type: How the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]
        if player:
            player.stop_all = False

        if song is None:
            return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs

        async with ctx.typing():
            result = self.get_song(song)  # Gets a video ID for the song
            player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player

            queue.put(player)  # Adds a song to the servers queue system

        return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs

    @commands.command(name='URL')
    async def url(self, ctx, *, url, queue_type='Player'):
        """
        Adds the specified url to the queue to be played
        :param ctx: Information on the context of where the command was called
        :param url: A url to be queued
        :param queue_type: How the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]
        if player:
            player.stop_all = False

        if url is None:
            return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs

        async with ctx.typing():
            player = await AudioSourcePlayer.download(url, loop=self.bot.loop, ctx=ctx)  # Creates a player

            queue.put(player)  # Adds a url to the servers queue system

        return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs

    @commands.command(name='Stream')
    async def stream(self, ctx, *, url, queue_type='Player'):
        """
        Adds the specified url to the queue to be played, only difference from url() and play() is that this does not pre-download songs to be played, it streams from an audio source
        :param ctx: Information on the context of where the command was called
        :param url: A url to be queued
        :param queue_type: How the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]
        if player:
            player.stop_all = False

        if url is None:
            return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs

        async with ctx.typing():
            player = await AudioSourcePlayer.download(url, loop=self.bot.loop, stream=True, ctx=ctx)  # Creates a player

            queue.put(player)  # Adds a url to the servers queue system

        return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs

    @commands.command(name='Pause')
    async def pause(self, ctx):
        """
        Pauses the current servers audio stream
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        ctx.message.guild.voice_client.pause()  # Pauses the audio stream
        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name=f"Paused {player.title}", value=f"{self.bot.command_prefix}{ctx.command.qualified_name} to resume the song")
        await ctx.send(embed=embed)

    @commands.command(name='Resume')
    async def resume(self, ctx):
        """
        Resumes the current servers audio stream
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        ctx.message.guild.voice_client.resume()  # Resumes the audio stream
        await ctx.send(f"Resumed {player.title}")

    @commands.command(name='Skip')
    async def skip(self, ctx):
        """
        Skips the current song being played
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        if 'skip' in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Skip", player, ctx)
        if passed:
            ctx.message.guild.voice_client.stop()  # Kills the audio stream
            await ctx.send(f"Sorry {player.requester}, but we decided to skip `{player.title}`")
            return await self.play_next_song(ctx)
        else:
            await ctx.send(f"The people have spoken! We will continue playing {player.title}!")

    @commands.command(name='Stop', aliases=['Quit'])
    async def stop(self, ctx):
        """
        Stops all music
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        if 'stop' in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Stop", player, ctx)
        if passed:
            player.stop_all = True
            ctx.message.guild.voice_client.stop()  # Kills the audio stream
            await ctx.send(f"Ok! If you want to continue playing music do `{self.bot.command_prefix}play`!")
            return await self.play_next_song(ctx)
        else:
            await ctx.send(f"You cant stop me! No one can!!!")

    @commands.command(name='Volume', aliases=['Vol'])
    async def volume(self, ctx, vol: int = None):
        """
        Sets the volume for the player
        :param ctx: Information on the context of where the command was called
        :param vol: the volume for the player, 0-100
        """
        if vol < 0:
            vol = 0
        elif vol > 100:
            vol = 100
        player = self.players[ctx.guild.id]
        if vol is None:
            return await ctx.send(f"Player volume set to {player.volume}")
        player.volume = float(vol/100)
        return await ctx.send(f"Set the volume to {vol}%")

    @commands.command(name='NowPlaying', aliases=['Current'])
    async def nowplaying(self, ctx):
        """
        Displays the current song name along with the next song in the queue
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]
        embed = discord.Embed(title='Song Information', color=discord.Color.green())
        embed.add_field(name=f"Current Song: {player.title} | Requested by *{player.requester}*", value=f"Next Up: {queue.next_up()}")
        embed.add_field(name=f"Song Artist", value=player.data['artist'])
        embed.set_footer(text=f"Queue Length: {len(queue.queue)}")
        await ctx.send(embed=embed)

    @commands.command(name='Queue', aliases=[])  # Very messy, needs to be cleaned up. Maybe with a pagination class
    async def queue(self, ctx):
        """Displays the current song queue in a paginated embed
        :param ctx: Information on the context of where the command was called
        """
        queue = self.queues[ctx.guild.id]

        first = 0
        second = 10
        curr_page = 1
        left = "\N{BLACK LEFT-POINTING TRIANGLE}"
        stop = "\N{BLACK SQUARE FOR STOP}"
        right = "\N{BLACK RIGHT-POINTING TRIANGLE}"

        total = [f"{enum+1}. {song.title} - Requested by *{song.requester}*" for enum, song in enumerate(queue.queue[::-1])]

        if len(total) > 10:
            embed = discord.Embed(color=discord.Color.teal())
            embed.add_field(name=f"Music Queue", value='\n'.join(total[first:second]))
            embed.set_footer(text=f"Total: {len(total)} | Page {curr_page}/{math.ceil(len(total) / 10)}")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(left)
            await msg.add_reaction(stop)
            await msg.add_reaction(right)

            while True:
                react, user = await self.bot.wait_for('reaction_add', check=lambda u_react, u_user: u_user.id == ctx.author.id, timeout=20.0)

                if react.emoji == left:
                    first -= 10
                    second -= 10
                    curr_page -= 1
                    if first < 0:
                        first = 0
                    if second < 10:
                        second = 10
                    if curr_page < 0:
                        curr_page = 0

                elif react.emoji == stop:
                    break

                elif react.emoji == right:
                    first += 10
                    second += 10
                    curr_page += 1
                    if first > len(total) - 10:
                        first = len(total) - 10
                    if second > len(total):
                        second = len(total)
                    if curr_page > math.ceil(len(total) / 10):
                        curr_page = math.ceil(len(total) / 10)

                newEmbed = discord.Embed(color=discord.Color.teal())
                newEmbed.add_field(name=f"Music Queue", value='\n'.join(total[first:second]))
                newEmbed.set_footer(text=f"Total: {len(total)} | Page {curr_page}/{math.ceil(len(total) / 10)}")
                await msg.edit(embed=newEmbed)
        else:
            if len(total) == 0:
                embed = discord.Embed(color=discord.Color.teal())
                embed.add_field(name=f"Music Queue", value=f"There are currently no songs in the queue! Add one using the `{self.bot.command_prefix}play`, `{self.bot.command_prefix}url` or `{self.bot.command_prefix}stream` commands!")
                embed.set_footer(text="Total: 0 | Page 1/1")
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=discord.Color.teal())
                embed.add_field(name=f"Music Queue", value='\n'.join(total))
                embed.set_footer(text=f"Total: {len(total)} | Page {curr_page}/{math.ceil(len(total) / 10)}")
                await ctx.send(embed=embed)

    @commands.command(name='Remove')
    async def remove(self, ctx, song_num: int):
        """
        Removes an item from the queue
        :param ctx: Information on the context of where the command was called
        :param song_num: The song number in the queue to remove
        """
        queue = self.queues[ctx.guild.id]

        song = queue.find(song_num)
        if not song:
            embed = discord.Embed(title="Failed to remove song", color=discord.Color.red())
            embed.add_field(name="Sorry but I could not find that song!", value="Please make sure that you used the correct song ID!")
            embed.set_footer(text=f"Example: {self.bot.command_prefix}{ctx.command.qualified_name} 1")
            return await ctx.send(embed=embed)

        if song.requester == ctx.author or "queueremove" in self.user.perms:
            passed = True
        else:
            passed = self.start_vote("Queue Remove", song, ctx)

        if passed:
            queue.remove(song_num)
            embed = discord.Embed(title="Removed a song", color=discord.Color.green())
            embed.add_field(name=song.title, value="We have removed the song from the queue!")
            return await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Failed to remove song", color=discord.Color.red())
            embed.add_field(name="The people have spoken!", value=f"{song.title} stays!")
            return await ctx.send(embed=embed)

    @commands.command(name="Clear", aliases=['qClear'])
    async def clear(self, ctx):
        """
        Clears the queue of all songs
        :param ctx: Information on the context of where the command was called
        """
        queue = self.queues[ctx.guild.id]
        if "queueclear" in self.user.perms:
            passed = True
        else:
            passed = self.start_vote("Queue Clear", None, ctx)
        if passed:
            for song in range(len(queue.queue)):
                queue.remove(song)
            embed = discord.Embed(title="The queue has been cleared!", color=discord.Color.green())
            embed.add_field(name="The current song will continue to be played", value=f"You can stop it with the `{self.bot.command_prefix}stop` or `{self.bot.command_prefix}skip` commands")
            embed.set_footer(text=f"After this song is finished, an auto playlist will start")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="The queue stays!", color=discord.Color.green())
            embed.add_field(name="The queue may not be cleared but at least you have some 🎵music🎵 playing", value=f"If you have your own song in the queue you wish to remove, use {self.bot.command_prefix}remove <song_id>")
            await ctx.send(embed=embed)

    @commands.command(name='Save')
    async def save(self, ctx):
        """
        Saves the current queue into the servers saved queue list
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]  # Our queue list
        saved = SavedQueues(bot=self.bot, ctx=ctx)  # All of our saved queues
        queues = eval(saved.get_saved_queues())  # Get our saved queues
        queues.update({f'{len(queues.keys())}': [player.title] + [song.title for song in queue.queue]})
        saved.update(queues)
        await ctx.send(f"I saved the queue for you! Check it out with `{self.bot.command_prefix}queues`")

    @commands.command(name='Delete')
    async def delete(self, ctx, qid: int):
        """
        Deletes a queue from the list of saved queues
        :param ctx: Information on the context of where the command was called
        :param qid: The queue id to delete from
        """
        saved = SavedQueues(bot=self.bot, ctx=ctx)  # All of our saved queues
        queues = eval(saved.get_saved_queues())  # Get our saved queues
        queues.pop(str(qid - 1))
        saved.update(queues)
        await ctx.send(f"Ok, I removed that from the saved queue list")

    @commands.command(name='Load')
    async def load(self, ctx, queue_id: int):
        """
        Loads the specified queue into the current queue
        :param ctx: Information on the context of where the command was called
        :param queue_id: The queue id to load into the current queue
        """
        saved = SavedQueues(bot=self.bot, ctx=ctx)
        queues = eval(saved.get_saved_queues())
        await ctx.send(f"Loading Queue...")
        async with ctx.typing():
            for song in queues[str(queue_id - 1)]:
                result = self.get_song(song)  # Gets a video ID for the song
                player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player
                queue = self.queues[ctx.guild.id]
                queue.put(player)  # Adds a song to the servers queue system
        await ctx.send(f"Queue Loaded!")
        return await self.play_next_song(ctx, 'Auto')  # Starts to play queued songs

    @commands.command(name='Saved', aliases=['Queues'])
    async def saved(self, ctx):
        """
        List of all saved queues the server has
        :param ctx: Information on the context of where the command was called
        """
        async with ctx.typing():
            saved = SavedQueues(bot=self.bot, ctx=ctx)
            queues = eval(saved.get_saved_queues())
            saved_queues = []
            current_page = 0
            left = "\N{BLACK LEFT-POINTING TRIANGLE}"
            stop = "\N{BLACK SQUARE FOR STOP}"
            right = "\N{BLACK RIGHT-POINTING TRIANGLE}"
            for queue, songs in queues.items():
                saved_queues.append([f"Queue ID: {int(queue) + 1:,}", '\n'.join(songs),
                                     f"Page {int(queue) + 1:,} / {len(queues):,} | Total: {len(songs):,}"])
            embed = discord.Embed(title="Saved Queues", color=discord.Color.green())
            embed.add_field(name=saved_queues[0][0], value=saved_queues[0][1])
            embed.set_footer(text=saved_queues[0][2])
            message = await ctx.send(embed=embed)
        for reaction in [left, stop, right]:
            await message.add_reaction(reaction)
        while True:
            react, user = await self.bot.wait_for('reaction_add',
                                                  check=lambda u_react, u_user: u_user.id == ctx.author.id,
                                                  timeout=20.0)
            if react.emoji == left:
                current_page -= 1
            elif react.emoji == stop:
                break
            elif react.emoji == right:
                current_page += 1
            else:
                continue
            if current_page < 0:
                current_page = 0
            elif current_page > len(saved_queues) - 1:
                current_page = len(saved_queues) - 1

            await react.remove(ctx.author)

            embed = discord.Embed(title="Saved Queues", color=discord.Color.green())
            embed.add_field(name=saved_queues[current_page][0], value=saved_queues[current_page][1])
            embed.set_footer(text=saved_queues[current_page][2])
            await message.edit(embed=embed)
        await react.remove(ctx.author)

    @commands.command(name='Repeat')
    async def repeat(self, ctx, *, repeat_type='song'):
        """
        Plays the queue on loop, including the current song
        :param ctx: Information on the context of where the command was called
        :param repeat_type: The type of item we will repeat
        """
        if repeat_type == 'song':
            player = self.players[ctx.guild.id]
            player.repeat = not player.repeat
            embed = discord.Embed(title="Song Repeat has been toggled!", color=discord.Color.green())
            embed.add_field(name=f"Song repeat is set to {player.repeat}!", value="The current song will now be repeated" if player.repeat else "The song will no longer repeat itself")
            await ctx.send(embed=embed)
        elif repeat_type.lower() == 'queue':
            queue = self.queues[ctx.guild.id]
            queue.repeat = not queue.repeat
            embed = discord.Embed(title="Queue Repeat has been toggled!", color=discord.Color.green())
            embed.add_field(name=f"Queue repeat is set to {queue.repeat}!", value="The current song and the queue will now be repeated" if queue.repeat else "The queue will no longer repeat itself")
            await ctx.send(embed=embed)
        else:
            return

    @commands.command(name='Shuffle')
    async def shuffle(self, ctx):
        """
        Shuffles the current queue
        :param ctx: Information on the context of where the command was called
        """
        queue = self.queues[ctx.guild.id]
        random.shuffle(queue.queue)
        embed = discord.Embed(name="Shuffled!", color=discord.Color.green())
        embed.add_field(name="I have shuffled the queue!", value=f"Use `{self.bot.command_prefix}queue` to view the new queue order")
        await ctx.send(embed=embed)

    @load.before_invoke
    @nowplaying.before_invoke
    @play.before_invoke
    @stream.before_invoke
    @url.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @skip.before_invoke
    @volume.before_invoke
    @queue.before_invoke
    @remove.before_invoke
    @clear.before_invoke
    @save.before_invoke
    @shuffle.before_invoke
    @repeat.before_invoke
    async def ensure_voice_ready(self, ctx):
        """
        This will make sure that the bot is in a voice channel before any music command is ran and that there is a queue system set up for the guild
        :param ctx: Information on the context of where the command was called
        """
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = Queue()

        if ctx.guild.id not in self.players:
            self.players[ctx.guild.id] = None

        if not ctx.message.guild.voice_client:
            await self.join(ctx)

    @commands.command(name='Override', aliases=['add_perm'])
    @commands.has_permissions(manage_guild=True)
    async def override(self, ctx, perm, member: discord.Member=None):
        """
        Test command to add permission overrides suck as skip, queue clear, ect
        :param ctx: Information on the context of where the command was called
        :param member: The user to add the over-ride permission to
        :param perm: The over-ride permission to add to the user; corresponding to permissions.json
        """
        if member is None:
            member = ctx.author

        user = User(bot=self.bot, ctx=ctx, user=member)
        added = user.add_permission(perm)
        if added:
            await ctx.send(f"Ok! {member.name} has the '{perm.lower().capitalize()}' override permission!")
        else:
            await ctx.send(f'Sorry, cant do that...Use `{self.bot.command_prefix}ValidPermissions` to view all valid permission names')


def setup(bot):
    bot.add_cog(Music(bot))
