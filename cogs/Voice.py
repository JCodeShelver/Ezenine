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
    async def from_url(cls, url, *, loop = None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download = False))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data = data)


class Voice(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def toggle_mute(self, ctx: commands.Context):
        await ctx.guild.change_voice_state(channel = ctx.voice_client.channel, self_mute = not ctx.me.voice.self_mute)

    # Joins the author's vc.
    @commands.command()
    async def join(self, ctx: commands.Context):
        if ctx.author.voice.channel is not None:
            return await ctx.guild.change_voice_state(channel = ctx.author.voice.channel, self_deaf = True)
        else:
            await ctx.channel.send("You must be in a voice channel for me to join!")

    # Plays a song from a url.
    @commands.command()
    async def play(self, ctx: commands.Context, *, url: str):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop = self.client.loop)
            
            ctx.voice_client.play(player, after = lambda e: print(f'Player error: {e}') if e else None)

        await ctx.send(f'Now playing: {player.title}')

    # Pause command.
    @commands.command()
    async def pause(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            ctx.voice_client.pause()
        else:
            botmsg = await ctx.channel.send("You don\'t have permission to use that command!")
            await asyncio.sleep(2)
            await botmsg.delete()
        
    # Stop command.
    @commands.command()
    async def stop(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            ctx.voice_client.stop()
        else:
            botmsg = await ctx.channel.send("You don\'t have permission to use that command!")
            await asyncio.sleep(2)
            await botmsg.delete()
        
    # Resume command.
    @commands.command()
    async def resume(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            ctx.voice_client.resume()
        else:
            botmsg = await ctx.channel.send("You don\'t have permission to use that command!")
            await asyncio.sleep(2)
            await botmsg.delete()

    # Leave command.
    @commands.command()
    async def leave(self, ctx: commands.Context):
        if "DJ" in [role.name for role in ctx.author.roles]:
            await ctx.voice_client.disconnect()
        else:
            botmsg = await ctx.channel.send("You don\'t have permission to use that command!")
            await asyncio.sleep(2)
            await botmsg.delete()

    @commands.command()
    async def skip(self, ctx: commands.Context):
        pass
    
    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def remove(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(voice_channel = None)

    @commands.command()
    async def move(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().conver(ctx, person)
        await target.edit(voice_channel = ctx.voice_client.channel)

    @commands.command()
    async def mute(self, ctx: commands.Context, person):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(mute = not target.voice.mute)

    @commands.command()
    async def deafen(self, ctx: commands.Context, person: str):
        target = await commands.MemberConverter().convert(ctx, person)
        await target.edit(deafen = not target.voice.deaf)

    @play.before_invoke
    @pause.before_invoke
    @skip.before_invoke
    @stop.before_invoke
    @resume.before_invoke
    @leave.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.guild.change_voice_state(channel = ctx.author.voice.channel, self_deaf = True)
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

def setup(client):
    client.add_cog(Voice(client))