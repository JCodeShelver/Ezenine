import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout
import itertools
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

    # The name indicates its purpose, its job is to reobtain the audiosource for an audio stream.
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
    # Something something makes attribute lookup faster bc memory saved (idfk).
    __slots__ = ('_client', '_ctx', '_guild', 'queue', 'next', 'last', 'interrupt', 'current', 'lastSource', 'postponedSource', 'now', 'np', 'volume')
    
    def __init__(self, ctx: commands.Context):
        self._client = ctx.bot
        self._ctx = ctx
        self._guild = ctx.guild
        
        self.queue = asyncio.Queue()    # The actual Queue
        
        # These are things that allow me to block (literally) execution of code until something happens.
        self.next = asyncio.Event() # This is set to true once the song ends.
        self.last = asyncio.Event() # This is set to true when using the back command.
        self.interrupt = asyncio.Event()

        self.volume = 0.5   # The default volume is 50%
        
        self.np = None  # This is to be set as a message object.

        # These will be sources. 
        self.current = None
        self.now = None
        self.lastSource = None
        self.postponedSource = None

        self._client.loop.create_task(self.gPlayerLoop())

    # The actual method that is called per guild to iterate thorugh the queue.
    async def gPlayerLoop(self):
        await self._client.wait_until_ready()    # Wait until the Bot's cache is ready.
        
        self.last.clear()   # By default, we are not in the "backwards" mode.
        self.interrupt.clear()  # By default, we are not playing a source right Goddamn now.
        
        # These two lines are ONLY here bc of my linter complaining about unboundedness.
        sourceData = None
        source = None
        
        while not self._client.is_closed():  # While the bot isn't offline:
            self.next.clear()   # Set the flag for going to the next song to false.

            if not (self.last.is_set() or self.interrupt.is_set()):  # Are we in normal operation mode?
                if self.postponedSource:
                    sourceData = self.postponedSource
                    
                    self.postponedSource = None
                else:
                    try:
                        # Wait for the next song. If we timeout cancel the player and disconnect...
                        async with timeout(300):  # 5 minutes...
                            sourceData = await self.queue.get()
                    except asyncio.TimeoutError:
                        return self.destroy(self._ctx.guild)
                
            # Is the last flag true?
            elif self.last.is_set() and not self.interrupt.is_set():
                sourceData = self.lastSource    # Play LS.
            
            # So the Interrupt flag must be true?
            elif self.interrupt.is_set() and not self.last.is_set():
                sourceData = self.now   # Play NOW.
            
            # So we're doing hybrid.
            elif self.interrupt.is_set() and self.last.is_set():
                sourceData = self.now

            if not isinstance(sourceData, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.prevent_my_pain(sourceData, loop = self._client.loop)
                except Exception as e:
                    await self._ctx.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume # Sets volume of source to the class' volume, so that volume doesn't reset after each song.
            self.current = source
            
            # Play the source loaded and set the next flag to true when done.
            self._ctx.voice_client.play(source, after = lambda _: self._client.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._ctx.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()  # Doesn't proceed until the next flag is set to true.

            # This giant chunk of comments is to help understand it. It's pretty spaghetti, so don't 
            # worry if it makes no goddamn cents. Heads up, this is a clusterfuck, this is at your 
            # own risk, and I don't have any TL;DR.

            # The following charts use "0" for None, pipe symbols (|) for a lack of change in the
            # variable from the last step, a as some song (song a), b as some other song (song b) 
            # that plays (or is played, or will be played) after a, and N as self.now, the song that
            # interrupts what's playing to do it's own thing. LS is an abbreviation for
            # self.lastSource, PPS is an abbreviation for self.postponedSource, and NP is an
            # abbreviation for "Now Playing".
            # Back-Now means that .now was invoked, then .back. A Now-Back is .back then  .now.

            # Normal Flow.          Back Flow.              Now Flow (works when LS is set as well)
            # When  LS  PPS NP      LS  PPS NP              LS  PPS NP
            # 0S    0   0   a       0   0   a               0   0   a   :Interrupt 1
            # 0E    a   |   X       a   |   X               |   a   X
            # 1S    ¦   |   b       |   ¦   b   :Last 1     |   |   N
            # 1E    b   |   X       |   b   X               |   ¦   X   :Interrupt 0
            # 2S    ¦   |   c       |   |   a               |   0   a
            # 2E    c   |   X       |   ¦   X   :Last 0     See Normal.
            # ...............       |   0   b
            #                       See Normal.
            #
            # Back-Now Flow.                                            Now-Back Flow.
            # 0S    0   0   a                                           0   0   a
            # 0E    a   |   X                                           a   |   X
            # 1S    |   ¦   b   :Interrupt 1                            |   ¦   b   :Back 1
            # 1E    |   b   X                                           |   b   X
            # 2S    |   |   N   :Skip, not Last 1, and Interrupt 0      |   |   a   :Interrupt 1
            # 2E    |   ¦   X                                           |   |   X
            # 3S    |   0   b                                           |   |   N   :Interrupt 0
            # 4S    See Normal.                                         |   |   X
            # 4E                                                        |   |   a   :Back 0
            # 5S                                                        |   ¦   X
            # 5E                                                        |   0   b
            #                                                           See Normal.

            # Update LS is PPS and NP are not the same (i.e. we are not doing special code nor do we have any flags high)
            if not (self.last.is_set() or self.interrupt.is_set()) and not (self.postponedSource == sourceData):
                self.lastSource = sourceData

            # Updates vars related to last and interrupt that have to take the value of what's currently playing.
            if (self.last.is_set() ^ self.interrupt.is_set()):
                # If we are in back, and a is playing.
                if self.lastSource == sourceData:
                    self.last.clear()
                
                #If we are in now, and now is playing.
                elif self.now == sourceData:
                    self.interrupt.clear()
                    self.now = None
                
                # A Now-in-Now has occurred. Don't turn off the flag, just go around again.
                elif self.postponedSource and self.postponedSource != sourceData and self.interrupt.is_set():
                    pass

                else:
                    # Set PPS on 0E
                    self.postponedSource = sourceData

            # You may think that an if statement with a condition of the flags being an AND would lead to
            # code inside that is seperate based on if Now occured after a Back, or vice versa. You are
            # wrong. A Back in Now scenario is handled by skipping. It goes back to b. NOW songs are 
            # treated as if they don't exist in the history (they're artifical).
            elif self.last.is_set() and self.interrupt.is_set():
                if self.now == sourceData:
                    # It turns out, passing it to the code from self.last in this state works fine.
                    self.interrupt.clear()
            
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
        return self._client.loop.create_task(self._ctx.cog._cleanup(guild))

# This is the actual cog (wow!)
class Voice(commands.Cog):
    # On initialization, set the client attribute to the bot and _queue attribute to a dict.
    def __init__(self, client: commands.Bot):
        self._client = client
        self._queue = {}

    # When we kill a GuildPlayer instance...
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
    
    # Returns a GuildPlayer instance, even if it doesn't exist (it makes one on the spot).
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
    @commands.is_owner()
    async def self_mute_(self, ctx: commands.Context):
        await ctx.guild.change_voice_state(channel = ctx.voice_client.channel, self_mute = not ctx.me.voice.self_mute)

    # Adds a song to the queue.
    @commands.command(name = "play", aliases = ["add", "p"])
    async def play_(self, ctx: commands.Context, *, url: str):
        await ctx.message.delete()
        
        async with ctx.typing():
            player = self._getGuildPlayer(ctx)  # Get your GuildPlayer instance.

            # Convert your pathetic url string into a buff info dictionary.
            source = await YTDLSource.from_url(ctx, url, loop = self._client.loop)

            await player.queue.put(source)  # Insert ;) the *buff* dictionary into the queue.
    
    # Plays a song right now damnit.
    @commands.command(name = "now", aliases = ["interrupt, rush"])
    async def now_(self, ctx: commands.Context, *, url: str):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently connected to a vc!", delete_after = 2)
            
            player = self._getGuildPlayer(ctx)
            player.interrupt.set()
            
            # We have to handle circumstances where now is used in tandem with back. No special code
            # is required for a now in now, as it will just overwrite player.now, and gets detected
            # internally.
            player.now = await YTDLSource.from_url(ctx, url, loop = self._client.loop) # The name is like right now, but I'm left handed.
            
            ctx.voice_client.stop()

            await ctx.send(f"{ctx.author} has a song that they just need to share!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)

    # Goes back to the last song in the queue.
    @commands.command(name = "back", aliases = ["rewind"])
    async def back_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently in a vc!", delete_after = 2)
            
            if ctx.voice_client.is_paused():    # Are we paused?
                pass
            elif not ctx.voice_client.is_playing(): # We're not? But we're still not playing? Mission Abort!
                return

            # Get the GuildPlayer instance and set the last flag to true.
            player = self._getGuildPlayer(ctx)
            
            # We have to handle circumstances where back is used in tandem with now (you never know what they do
            # to you child the first time.) A Back in Back scenario is handled by just skipping the song.

            # We do however, need to handle a Back in Now scenario...
            if player.interrupt.is_set() and not player.last.is_set():
                player.interrupt.clear()
                self.now = None
            else:   # If we are in a normal to Back, DO IT.
                player.last.set()

            # Stop it like normal.
            ctx.voice_client.stop()

            await ctx.send(f"{ctx.author} wanted to **rewind** the turntable!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
        
    # Skips the current playing song in the queue. 
    @commands.command(name = "skip", aliases = ["next", "scratch"])
    async def skip_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            # So we're either not in a vc or we are but not playing anything? Are you ready for a bad time?
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!")
            
            if ctx.voice_client.is_paused():    # Are we paused?
                pass
            elif not ctx.voice_client.is_playing(): # So we aren't, but we're not playing? Mission Abort.
                return

            # Standard stop of the source.
            ctx.voice_client.stop()

            await ctx.send(f"{ctx.author} can't party to that song!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
    
    # Pauses the currently playing song in the queue.
    @commands.command(name = "pause", aliases = ["halt", "zawarudo"])
    async def pause_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            # So we aren't in a vc or we aren't playing anything? That's -- no good!
            if not ctx.voice_client or not ctx.voice_client.is_playing():
                return await ctx.send("I am not currently playing anything!")
            elif ctx.voice_client.is_paused():  # We're already paused? Don't want to get an error.
                return
            
            ctx.voice_client.pause()
 
            await ctx.send(f"{ctx.author} postponed the fun!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
        
    # Resumes the current song in the queue.
    @commands.command(name = "resume", aliases = ["continue", "revive", "resurrect"])
    async def resume_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            # We have to be in a voice channel and connected, to resume anything.
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!")
            elif not ctx.voice_client.is_paused():  # We also have to be paused to resume (ya know, like normal).
                return
            
            ctx.voice_client.resume()

            await ctx.send(f"{ctx.author} just revived the party!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)

    # Stops the currently playing song in the queue, deletes the guild's instance of the GuildPlayer class, and disconnects from voice.
    @commands.command(name = "stop", aliases = ["leave", "iiho"]) # iiho = 'Ight Im'ma head out
    async def stop_(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            # No vc or playing of anything? Why stop what doesn't exist?
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!", delete_after = 2)
            
            # Call the cleanup crew for our instance of GuildPlayer.
            await self._cleanup(ctx.guild)
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
    
    # Adjusts the volume of the GuildPlayer instance associated with the guild.
    @commands.command(name = "volume", aliases = ["vol", "v"])
    async def volume_(self, ctx: commands.Context, volume: int):
        # Don't do anything if there's no difference, and make sure that if there is, that the value is valid.
        if "DJ" in [role.name for role in ctx.author.roles]:
            if volume / 100 == ctx.voice_client.source.volume:
                return
            elif volume > 100:
                volume = 100
            elif volume < 0:
                volume = 0
            
            if ctx.voice_client:    # So we're connected?
                ctx.voice_client.source.volume = volume / 100

            gPlayer = self._getGuildPlayer(ctx)

            # This & freshVol are used to determine the message used (did we turn it up or down?).
            ogVol = gPlayer.volume * 10
            
            gPlayer.volume = volume / 100
            
            freshVol = gPlayer.volume * 10

            await ctx.send(f"{ctx.author} just {'cranked' if ogVol < freshVol else 'hushed'} it to {freshVol}!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)

    # Disconnects the specified person from voice.
    @commands.command(name = "remove", aliases = ["timeout"])
    async def remove_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        
        if target is ctx.guild.me:  # If the target is the bot, just use .leave.
            return await ctx.invoke(self.leave)

        await target.edit(voice_channel = None)

    # Moves the specified person from their voice channel to the bot's current voice channel.
    @commands.command(name = "move", aliases =["shift", "attract"])
    @commands.check_any(commands.has_guild_permissions(move_members = True), commands.has_guild_permissions(administrator = True))
    async def move_(self, ctx: commands.Context, channel, *, person):
        channel = await commands.VoiceChannelConverter().convert(ctx, channel)
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(voice_channel = channel)

    # Server mutes the specified person.
    @commands.command(name = "vmute", aliases = ["silence"])
    @commands.check_any(commands.has_guild_permissions(mute_members = True), commands.has_guild_permissions(administrator = True))
    async def mute_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(mute = not target.voice.mute)

    # Server deafens the specified person.
    @commands.command(name = "deafen", aliases = ["deaf", "muffle"])
    @commands.check_any(commands.has_guild_permissions(deafen_members = True), commands.has_guild_permissions(administrator = True))
    async def deafen_(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(deafen = not target.voice.deaf)

    # Returns up to the first five entries in the queue.
    @commands.command(name = "q", aliases = ["qc", "queue"])
    async def queue_(self, ctx: commands.Context):
        await ctx.message.delete()

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send("I am not currently playing anything!")
        
        player = self._getGuildPlayer(ctx)
        
        if not player.current:
            return await ctx.send("I am not currently playing anything!", delete_after = 2)

        if player.queue.empty():
            if player.lastSource and not player.last.is_set():
                _desc = (f'**Last played: **`{player.lastSource["title"]}` requested by `{player.lastSource["requester"]}`.\n\n'
                        f'**Now Playing: **`{player.current["title"]}` requested by `{player.current["requester"]}`.\n\n'
                        f'The queue is empty.')
            else:
                _desc = (f'**Now Playing: **`{player.current["title"]}` requested by `{player.current["requester"]}`.\n\n'
                        f'The queue is empty.')
        
        else:
            _head = list(itertools.islice(player.queue._queue, 0, 5))
            _head_info = '\n'.join(f'**{_head.index(_) + 1}. **`{_["title"]}` requested by `{_["requester"]}`.' for _ in _head)
        
            if player.lastSource and not player.last.is_set():
                _desc = (f'**Last played: **`{player.lastSource["title"]}` requested by `{player.lastSource["requester"]}`.\n\n'
                        f'**Now Playing: **`{player.current["title"]}` requested by `{player.current["requester"]}`.\n\n'
                        f'{_head_info}.')
            else:
                _desc = (f'**Now Playing: **`{player.current["title"]}` requested by `{player.current["requester"]}`.\n\n'
                        f'{_head_info}.')

        embed = discord.Embed(title = 'Queue Info', description = _desc)

        await ctx.send(embed = embed, delete_after = 20)

    # Returns the currently playing song.
    @commands.command(name = "whatis", aliases = ["np", "now_playing", "current", "curr", "playing"])
    async def whatis_(self, ctx: commands.Context):
        await ctx.message.delete()

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send("I am not currently connected to a vc!", delete_after = 2)
        
        player = self._getGuildPlayer(ctx)
        if not player.current:
            return await ctx.send("I am not not currently playing anything!", delete_after = 2)

        try:
            # Delete the old now playing message
            await player.np.delete()
        except discord.HTTPException:   # Catch an exception if it fails (e.g.: It got deleted already)
            pass

        player.np = await ctx.send(f"**Now Playing:** `{ctx.voice_client.source.title}` requested by "
                                   f"`{ctx.voice_client.source.requester}`", delete_after = 20)

    # Makes sure that the client has a voice client.
    @play_.before_invoke
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