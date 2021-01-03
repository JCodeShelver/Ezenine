import discord
from discord.ext import commands
import asyncio
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
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume = 0.5):
        super().__init__(source, volume)
        
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url: str, *, loop = None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download = False))

        if 'entries' in data:
            data = data['entries'][0]

        return cls(discord.FFmpegPCMAudio(data['url']), data = data)


class Voice(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self._vClient = None
        self._queue = {}

    @commands.command()
    async def self_mute(self, ctx: commands.Context):
        await ctx.guild.change_voice_state(channel = ctx.voice_client.channel, self_mute = not ctx.me.voice.self_mute)


    @commands.command()
    async def queue(self, ctx: commands.Context, *, url: str):
        async def _play_source():
            player = await YTDLSource.from_url(self._queue[str(ctx.guild.id)][0], loop = self.client.loop)
            self._vClient.play(player, after = lambda e: print(f"Player error: {e}") if e else None)

            await ctx.send(f'Now playing: {player.title}')
            
            if len(self._queue[str(ctx.guild.id)]) == 1:
                self._queue.pop(str(ctx.guild.id))
                await ctx.send("The queue has emptied!")
            else:
                self._queue.get(str(ctx.guild.id)).pop(0)
                await _play_source()

        async with ctx.typing():
            if str(ctx.guild.id) not in self._queue:
                self._queue[str(ctx.guild.id)] = []
                
            self._queue[str(ctx.guild.id)].append(url)
            
            if not self._vClient.source: 
                await _play_source()
                
    @commands.command()
    async def skip(self, ctx: commands.Context):
        pass
    
    # Pause command.
    @commands.command()
    async def pause(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            self._vClient.pause()
        else:
            await ctx.channel.send("You don\'t have permission to use that command!", delete_after = 2, reference = ctx.message, mention_author = True)
        
    # Stop command.
    @commands.command()
    async def stop(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            self._vClient.stop()
        else:
            await ctx.channel.send("You don\'t have permission to use that command!", delete_after = 2, reference = ctx.message, mention_author = True)
        
    # Resume command.
    @commands.command()
    async def resume(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            self._vClient.resume()
        else:
            await ctx.channel.send("You don\'t have permission to use that command!", delete_after = 2, reference = ctx.message, mention_author = True)

    # Leave command.
    @commands.command()
    async def leave(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            await self._vClient.disconnect()
        else:
            await ctx.channel.send("You don\'t have permission to use that command!", delete_after = 2, reference = ctx.message, mention_author = True)

    @commands.command()
    async def vClientCheck(self, ctx: commands.Context):        
        await ctx.send(self._vClient if self._vClient else "No Voice Client", delete_after = 10)
    
    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
        self._vClient.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def remove(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(voice_channel = None)

    @commands.command()
    async def move(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(voice_channel = self._vClient.channel)

    @commands.command()
    async def mute(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(mute = not target.voice.mute)

    @commands.command()
    async def deafen(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(deafen = not target.voice.deaf)

    @queue.before_invoke
    @skip.before_invoke
    async def ensure_voice(self, ctx: commands.Context):
        if not self._vClient:
            if not ctx.author.voice:
                await ctx.send(content = "You are not connected to a voice channel.", delete_after = 2)
                raise commands.CommandError("Author not connected to a voice channel.")
            else:
                if not ctx.guild.me.voice:
                    self._vClient = await ctx.author.voice.channel.connect()
                else:
                    self._vClient = await ctx.guild.me.voice.channel.connect()
                
                await ctx.guild.change_voice_state(channel = self._vClient.channel, self_deaf = True)

        elif self._vClient.is_playing():
            self._vClient.stop()
        

def setup(client: commands.Bot):
    client.add_cog(Voice(client))