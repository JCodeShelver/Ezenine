import discord
from discord.ext import commands

import asyncio
from async_timeout import timeout
import youtube_dl

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

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

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        
        self.requester = requester
        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):
        return self.__getattribute__(item)

    @classmethod
    async def from_url(cls, ctx: commands.Context, url: str, *, loop = None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url = url, download = False))

        if 'entries' in data:
            data = data['entries'][0]

        return {'webpage_url' : data['webpage_url'], 'requester': ctx.author, 'title' : data['title']}

    @classmethod
    async def prevent_my_pain(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url = data['webpage_url'], download = False))

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data = data, requester = requester)

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
        await self.client.wait_until_ready()

        while not self.client.is_closed():
            self.next.clear()

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

            source.volume = self.volume
            self.current = source

            self._ctx.voice_client.play(source, after = lambda _: self.client.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._ctx.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild: discord.Guild):
        """Disconnect and cleanup the player."""
        return self.client.loop.create_task(self._ctx.cog.cleanup(guild))

class Voice(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self._vClient = None
        self._queue = {}

    async def cleanup(self, guild: discord.Guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            print("Attribute Error on cleanup.")

        self._vClient = None

        try:
            del self._queue[str(guild.id)]
        except KeyError:
            print("Key Error on cleanup.")

    def _getGuildPlayer(self, ctx: commands.Context):
        try:
            player = self._queue[str(ctx.guild.id)]
        except KeyError:
            player = GuildPlayer(ctx)
            self._queue[str(ctx.guild.id)] = player
        
        return player

    @commands.command()
    async def self_mute(self, ctx: commands.Context):
        await ctx.guild.change_voice_state(channel = ctx.voice_client.channel, self_mute = not ctx.me.voice.self_mute)

    @commands.command(aliases = ["play"])
    async def queue(self, ctx: commands.Context, *, url: str):
        async with ctx.typing():
            player = self._getGuildPlayer(ctx)

            source = await YTDLSource.from_url(ctx, url, loop = self.client.loop)

            await player.queue.put(source)
                
    @commands.command()
    async def skip(self, ctx: commands.Context):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send("I am not currently playing anything!")
        
        if ctx.voice_client.is_paused():
            pass
        elif not ctx.voice_client.is_playing():
            return

        ctx.voice_client.stop()

        await ctx.send(f"{ctx.author} can't party to that song!")
    
    # Pause command.
    @commands.command()
    async def pause(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_playing():
                return await ctx.send("I am not currently playing anything!")
            elif ctx.voice_client.is_paused():
                return
            
            ctx.voice_client.pause()
 
            await ctx.send(f"{ctx.author} postponed the fun!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
        
    # Stop command.
    @commands.command()
    async def stop(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!", delete_after = 2)
            
            await self.cleanup(ctx.guild)
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)
        
    # Resume command.
    @commands.command()
    async def resume(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            if not ctx.voice_client or not ctx.voice_client.is_connected():
                return await ctx.send("I am not currently playing anything!")
            elif not ctx.voice_client.is_paused():
                return
            
            ctx.voice_client.resume()

            await ctx.send(f"{ctx.author} just revived the party!")
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)

    # Leave command.
    @commands.command()
    async def leave(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            await self.cleanup(ctx.guild)
        else:
            await ctx.send("You don\'t have permission to use that command!", delete_after = 2)

    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
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

    @commands.command()
    async def remove(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        
        if target is ctx.guild.me:
            return await ctx.invoke(self.leave)

        await target.edit(voice_channel = None)

    @commands.command()
    async def move(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(voice_channel = ctx.voice_client.channel)

    @commands.command()
    async def mute(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(mute = not target.voice.mute)

    @commands.command()
    async def deafen(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(deafen = not target.voice.deaf)

    @queue.before_invoke
    @volume.before_invoke
    async def _ensure_voice(self, ctx: commands.Context):
        if not self._vClient:
            if not ctx.author.voice:
                await ctx.send("You are not connected to a voice channel.", delete_after = 2)
                raise commands.CommandError("Author not connected to a voice channel.")
            else:
                if not ctx.guild.me.voice:
                    self._vClient = await ctx.author.voice.channel.connect()
                else:
                    self._vClient = await ctx.guild.me.voice.channel.connect()
                
                await ctx.guild.change_voice_state(channel = self._vClient.channel, self_deaf = True)

def setup(client: commands.Bot):
    client.add_cog(Voice(client))