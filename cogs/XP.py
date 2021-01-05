import discord
from discord.ext import commands

import asyncio
import json

# Cog for Experience
class Experience(commands.Cog):
    pass

def setup(client: commands.Bot):
    client.add_cog(Experience(client))