import discord
from discord.ext import commands

import asyncio
from async_timeout import timeout
import youtube_dl

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

# Standard options for Youtube_dl module.
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# Ensure that we reconnect if it drops a little.
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Class that finds and makes a stream from a youtube url.
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        # When we make an actual object of this, we have to make a PCMVolumeTransformer Source
        super().__init__(source)
        
        # Streaming url vars for later.
        self.requester = requester
        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):
        return self.__getattribute__(item)

    # This gets the data we need for a youtube stream when it's needed.
    @classmethod
    async def from_url(cls, ctx: commands.Context, url: str, *, loop = None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url = url, download = False))

        if 'entries' in data:   # This makes it so we only take the first video if a playlist is sent.
            data = data['entries'][0]
        
        await ctx.send(f"**Just queued:** `{data['title']}` as requested by `{ctx.author}`!", delete_after = 20)

        # This dict has all the info we need for making a source later.
        return {'webpage_url' : data['webpage_url'], 'requester': ctx.author, 'title' : data['title']}

    @classmethod
    async def prevent_my_pain(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        
        # We "regather" the audio source (just reobtaining from the interwebs) via the data inputted.
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url = data['webpage_url'], download = False))

        # This returns an audiosource that has the necessary data, as well as the needed FFmpeg flags to not shit itself.
        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data = data, requester = requester)

# Class that defines a loop on a per-guild basis for a queue.
class GuildPlayer:
    def __init__(self, ctx: commands.Context):
        self.client = ctx.bot
        self._ctx = ctx
        
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.volume = 0.5
        self.np = None
        self.current = None

        self.client.loop.create_task(self.gPlayerLoop())

    async def gPlayerLoop(self):
        await self.client.wait_until_ready()    # Wait until the Bot's cache is ready.

        while not self.client.is_closed():  # While the bot isn't offline:
            self.next.clear()   # Set the flag for going to the next song to false.

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._ctx.guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.prevent_my_pain(source, loop = self.client.loop)
                except Exception as e:
                    await self._ctx.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume # Sets volume of source to the class' volume, so that volume doesn't reset after each song.
            self.current = source
            
            # Play the source loaded and set the internal flag to true when done.
            self._ctx.voice_client.play(source, after = lambda _: self.client.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._ctx.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()  # Doesn't proceed until the internal flag is set to true.

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
               pass

    # Call the cleanup in the cog class when needed (with guild inputted so as to kill this instance of this class)
    def destroy(self, guild: discord.Guild):
        """Disconnect and cleanup the player."""
        return self.client.loop.create_task(self._ctx.cog._cleanup(guild))

class Voice(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self._queue = {}

    async def _cleanup(self, guild: discord.Guild):
        try:
            # Try to disconnect the voice client of the guild.
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            # Try to also kill the GuildPlayer instance associated with the guild.
            del self._queue[guild.id]
        except KeyError:
            pass
    
    def _getGuildPlayer(self, ctx: commands.Context):
        try:
            # Try and access the GuildPlayer instance associated with guild.
            player = self._queue[ctx.guild.id]
        except KeyError:    # And then make it when it doesn't exist.
            player = GuildPlayer(ctx)
            self._queue[ctx.guild.id] = player
        
        return player

    # Mutes the bot (self mute, not server mute, so it really does nothing functionally).
    @commands.command(name = "self_mute")
    async def self_mute_(self, ctx: commands.Context):
        await ctx.guild.change_voice_state(channel = ctx.voice_client.channel, self_mute = not ctx.me.voice.self_mute)

    # Adds a song to the queue.
    @commands.command(name = "play", aliases = ["queue"])
    async def queue_(self, ctx: commands.Context, *, url: str):
        #await ctx.message.delete()
        
        async with ctx.typing():
            player = self._getGuildPlayer(ctx)

            source = await YTDLSource.from_url(ctx, url, loop = self.client.loop)

            await player.queue.put(source)

    # Skips the current playing song in the queue. 
    @commands.command(name = "skip", aliases = ["next", "scratch"])
    async def skip_(self, ctx: commands.Context):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send("I am not currently playing anything!")
        
        if ctx.voice_client.is_paused():
            pass
        elif not ctx.voice_client.is_playing():
            return

        ctx.voice_client.stop()

        await ctx.send(f"{ctx.author} can't party to that song!")
    
    # Pauses the currently playing song in the queue.
    @commands.command(name = "pause", aliases = ["halt", "zawarudo"])
    async def pause_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_playing():
                return await ctx.send("I am not currently playing anything!")
            elif ctx.voice_client.is_paused():
                return
            
            ctx.voice_client.pause()
 
            await ctx.send(f"{ctx.author} postponed the fun!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
        
    # Stops the currently playing song in the queue, deletes the guild's instance of the GuildPlayer class, and disconnects from voice.
    @commands.command(name = "stop", aliases = ["leave", "iiho"]) # iiho = 'Ight Im'ma head out
    async def stop_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!", delete_after = 2)
            
            await self._cleanup(ctx.guild)
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
        
    # Resumes the current song in the queue.
    @commands.command(name = "resume", aliases = ["continue", "revive", "resurrect"])
    async def resume_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!")
            elif not ctx.voice_client.is_paused():
                return
            
            ctx.voice_client.resume()

            await ctx.send(f"{ctx.author} just revived the party!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)

    # Adjusts the volume of the GuildPlayer instance associated with the guild.
    @commands.command(name = "volume", aliases = ["vol"])
    async def volume_(self, ctx: commands.Context, volume: int):
        if volume / 100 == ctx.voice_client.source.volume:
            return
        elif volume > 100:
            volume = 100
        elif volume < 0:
            volume = 0
        
        if ctx.voice_client:
            ctx.voice_client.source.volume = volume / 100

        gPlayer = self._getGuildPlayer(ctx)
        
        ogVol = gPlayer.volume * 10
        
        gPlayer.volume = volume / 100
        
        freshVol = gPlayer.volume * 10

        await ctx.send(f"{ctx.author} just {'cranked' if ogVol < freshVol else 'hushed'} it to {freshVol}!")

    # Disconnects the specified person from voice.
    @commands.command(name = "remove", aliases = ["timeout"])
    async def remove_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        
        if target is ctx.guild.me:
            return await ctx.invoke(self.leave)

        await target.edit(voice_channel = None)

    # Moves the specified person from their voice channel to the bot's current voice channel.
    @commands.command(name = "move", aliases =["shift", "attract"])
    async def move_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(voice_channel = ctx.voice_client.channel)

    # Server mutes the specified person.
    @commands.command(name = "mute", aliases = ["silence"])
    async def mute_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(mute = not target.voice.mute)

    # Server deafens the specified person.
    @commands.command(name = "deafen", aliases = ["deaf", "muffle"])
    async def deafen_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(deafen = not target.voice.deaf)

    # Makes sure that the client has a voice client.
    @queue_.before_invoke
    @volume_.before_invoke
    async def _ensure_voice(self, ctx: commands.Context):
        if not ctx.voice_client:
            if not ctx.author.voice:
                await ctx.send("You are not connected to a voice channel.", delete_after = 2)
                raise commands.CommandError("Author is not in a voice channel.")
            else:
                if not ctx.guild.me.voice:
                    await ctx.author.voice.channel.connect()
                else:
                    await ctx.guild.me.voice.channel.connect()
                
                await ctx.guild.change_voice_state(channel = ctx.voice_client.channel, self_deaf = True)

def setup(client: commands.Bot):
    client.add_cog(Voice(client))