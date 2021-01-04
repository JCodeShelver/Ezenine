import discord
from discord.ext import commands
import asyncio
import json

class xp(commands.Cog):
    pass

def setup(client: commands.Bot):
    client.add_cog(xp(client))