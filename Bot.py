import discord
from discord.ext import commands
import asyncio
import random
import json
import os
import logging

with open('/home/pi/Ezenine/botSettings.json', 'r') as f:
    settings = json.load(f)

logging.basicConfig(level = eval(settings["logLevel"]))

intents = discord.Intents.default()
intents.members = True

client = commands.Bot(command_prefix = settings["prefix"], intents = intents, owner_id = 409452148510949408)

sac = settings["sac"]
mac = settings["mac"]

replyignore = []
dmignore = []

players = {}

# Deletes any messages within a hitlist.
async def purgekillmsg(ctx, hitlist):
    for msg in hitlist:
        if msg.channel != ctx.channel:	# Deletes DM messages one by one, and removes them from hitlist.
            await msg.delete()
            hitlist.remove(msg)
    await ctx.channel.delete_messages(hitlist)	# Purges remaining messages.

# Predicates, one for checking if the message is same author, same channel, the other is for same author, in the DMs
def response(ctx):
    def pred(newmsg):
        return newmsg.author == ctx.author and newmsg.channel == ctx.channel
    return pred

def pm_response(ctx):
    def pred(newmsg):
        return newmsg.author == ctx.author and newmsg.channel.type == discord.ChannelType.private
    return pred

gamebook = {
    "MedievalUnion" : ["At the Sanctuary of Renuell",
                       "At the Ashes of Varengoth",
                       "Trekking Skull Mountain",
                       "Deep in the Catacombs of the Sword",
                       "On the Road to Hetra",
                       "In the City of Hetra",
                       "At the Temple of Silpo"],
    "Fun" : ["with people\"s heartstrings",
         "with cats",
         "with humans"]}

chat_filter = ["NIGGA", "FAG", "NIGGER", "FUCK", "PEPE", "YEET"]
bypass_list = [409452148510949408, 469129991544766475]

#region Events
@client.event
async def on_ready():
    await client.change_presence(activity = discord.Game(name = "Medieval Unions: Battling the Shadow Dragon"), status = discord.Status.online)
    print ("This is Ezenine, status: online. Connected to The Shadow Side.")

@client.event
async def on_message(message):
    global dmignore
    global replyignore
    
    # Do not process messages sent by bots.
    if message.author.bot:
        return
    
    context = await client.get_context(message)
    
    # DMs bypass the rest of the code, those not involved in commands get sent to #bot-dms.
    if message.guild == None:
        if message not in dmignore:
            await client.get_channel(464959332052762636).send(f"{message.author.name} said to me: {message.content}")
        else:
            pass
    elif context.valid or (message in replyignore):	# Messages that invoke commands or are used in wait_fors are ignored.
        pass
    else:
        # If it's in the server, contribute to xp system.
        if message.guild.id == 462277524542717973:
            with open('/home/pi/Ezenine/users.json', 'r') as f:
                users = json.load(f)

            update_data(users, message.author, True)
            add_experience(users, message.author, 5)
            await level_up(users, message.author, message.channel)
            await rank_up(users, message.author, message.channel)

            with open('/home/pi/Ezenine/users.json', 'w') as f:
                json.dump(users, f)
        
        # Chat filter
        for word in chat_filter:
            if word in message.content and message.author.id not in bypass_list:
                    try:
                        await message.delete()
                        await message.channel.send(f"**Hey {message.author.mention}!** You\'re not allowed to use that word here!")
                    except discord.errors.NotFound:
                        return     

    await client.process_commands(message)

@client.event
async def on_member_join(member):
    await client.get_channel(462277524542717975).send(f"{member.mention} joined the server! Give them a nice welcome!")
    await client.get_channel(505781896014331905).send(f"{member.mention} joined the server.")
    
    with open('/home/pi/Ezenine/users.json', 'r') as f:
        users = json.load(f)

    update_data(users, member, False)
    
    with open('/home/pi/Ezenine/users.json', 'w') as f:
        json.dump(users, f)

@client.event
async def on_member_remove(member):
    await client.get_channel(505781896014331905).send(f"{member.mention} left the server. :(")

@client.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        with open('/home/pi/Ezenine/users.json', 'r') as f:
            users = json.load(f)
        
        users[str(after.id)]["nickname"] = after.nick

        with open('/home/pi/Ezenine/users.json', 'w') as f:
            json.dump(users, f) 

@client.event
async def on_member_ban(guild, member):
    await client.get_channel(505781896014331905).send(f"{member.mention} has been banned from the server {guild.name}.")

@client.event
async def on_member_unban(guild, member):
    await client.get_channel(505781896014331905).send(f"{member.mention} has been unbanned from the server {guild.name}.")                 

#endregion Events

#region XP Functions

# Updates the users.json file for a user.
def update_data(users: dict, user: discord.Member, sentMessage: bool = False):
    # If a user is not present in the list, make an entry for them.
    if not str(user.id) in users:
        users[str(user.id)] = {}    # Add an array with their user id associated to it.
        users[str(user.id)]["name"] = user.name
        try:
            users[str(user.id)]["nickname"] = user.nick
        except Exception:
            pass
        users[str(user.id)]["experience"] = 0
        users[str(user.id)]["level"] = 1    # Start at level 1 because level 0 would break the level_up command.
        users[str(user.id)]["messages"] = 0
    
    if sentMessage:
        # If they actually sent a message (not being checked by msgcount), count messages
        users[str(user.id)]["messages"] += 1

# Increments a user's exp.
def add_experience(users, user, exp):
    users[str(user.id)]["experience"] += exp

# Checks whether a user should level up.
async def level_up(users, user, channel):
    if users[str(user.id)]["level"] < 500:
        exp = users[str(user.id)]["experience"]
        
        lvl_start = users[str(user.id)]["level"]
        lvl_end = int(exp ** (1/4))
        
        if lvl_start < lvl_end:	# Levels up if the fourth root of exp has an integer part greater than the current level.
            await channel.send(f"{user.mention} has leveled up to level {lvl_end}!")
            
            users[str(user.id)]["level"] = lvl_end

# Changes a user's rank if their message count is high enough.
async def rank_up(users, user, channel):
    # Get the user's msg count, roles, and route.
    messages = users[str(user.id)]["messages"]
    roles = user.roles
    
    if messages == 575000:
        role1 = discord.utils.get(user.guild.roles, name = "Total Darkness")
        role2 = discord.utils.get(user.guild.roles, name = "Umbral")
        roles[roles.index(role2)] = role1
        
        await user.edit(roles)
    elif messages == 300000:
        role1 = discord.utils.get(user.guild.roles, name = "Umbral")
        role2 = discord.utils.get(user.guild.roles, name = "Penumbral")
        roles[roles.index(role2)] = role1
        
        await user.edit(roles)
    elif messages == 135000:
        role1 = discord.utils.get(user.guild.roles, name = "Penumbral")
        role2 = discord.utils.get(user.guild.roles, name = "Wisp of Death")
        roles[roles.index(role2)] = role1

        await user.edit(roles)       
    elif messages == 50000:
        role1 = discord.utils.get(user.guild.roles, name = "Wisp of Death")
        role2 = discord.utils.get(user.guild.roles, name = "Blossoming Darkness")
        roles[roles.index(role2)] = role1
        
        await user.edit(roles)
    elif messages == 15000:
        role1 = discord.utils.get(user.guild.roles, name = "Blossoming Darkness")
        role2 = discord.utils.get(user.guild.roles, name = "Asset of the Void")
        roles[roles.index(role2)] = role1
        
        await user.edit(roles)
    elif messages == 5000:
        role1 = discord.utils.get(user.guild.roles, name = "Asset of the Void")
        role2 = discord.utils.get(user.guild.roles, name = "Ghost of Shadows")
        roles[roles.index(role2)] = role1
        
        await user.edit(roles)
    elif messages == 1750:
        role1 = discord.utils.get(user.guild.roles, name = "Ghost of Shadows")
        role2 = discord.utils.get(user.guild.roles, name = "Dim Soul")
        roles[roles.index(role2)] = role1
        
        await user.edit(roles)
    elif messages == 100:
        role1 = discord.utils.get(user.guild.roles, name = "Dim Soul")
        role2 = discord.utils.get(user.guild.roles, name = "Bright Soul")
        roles[roles.index(role2)] = role1

        await user.edit(roles)

# endregion XP Functions

#region Commands

# Close Bot correctly.
@client.command()
@commands.is_owner()
async def close(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    
    await client.close()
    await client.logout()

# A simple ping command
@client.command()
async def ping(ctx):
    await ctx.send(f"Pong! {client.latency * 1000}ms")

# A simple echoing command
@client.command()
async def echo(ctx, *args):    
    output = ""
    for word in args:
        output += word
        output += " "
    await ctx.send(output)

# Changes the "game" the bot is playing.
@client.command()
async def change_game(ctx, book = 0, type = "p", *game):
    # Setup of variables
    global gamebook
    sleepytime = 2
    type = type.lower()
    
    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    # Generic Reply Ignore use for message processing.
    global replyignore
    
    # Check if the book is used, display if so, otherwise set game to what is specified.
    if ctx.author.id in [409452148510949408, 469129991544766475]:
        try:
            if book == 1:
                temp = []
                dictlist = []
                
                for key, value in gamebook.items():
                    temp = [key, value]
                
                    dictlist.append(temp)
                
                await ctx.author.send(dictlist)
            elif book == 0:
                newgame = ""
                
                for word in game:
                    newgame += word
                    newgame += " "
                
                newgame = newgame.strip()
                
                dialog1 = await ctx.send("Do you want a url? Y/N")
                killmsg.append(dialog1)
                
                choice = await client.wait_for("message", check = response(ctx))
                replyignore.append(choice)
                killmsg.append(choice)
                
                if choice.content.upper() == "Y":
                    dialog2 = await ctx.send("Enter URL: ")
                    killmsg.append(dialog2)
                    
                    url = await client.wait_for("message", check = response(ctx))
                    replyignore.append(url)
                    killmsg.append(url)
                    url = url.content
                else:
                    url = None
                
                if type == "p":
                    type = discord.ActivityType.playing
                elif type == "s":
                    type = discord.ActivityType.streaming
                elif type == "l":
                    type = discord.ActivityType.listening
                elif type == "w":
                    type = discord.ActivityType.watching
                elif type == "c":
                    type = discord.ActivityType.competing
                else:
                    type = discord.ActivityType.playing
                
                await client.change_presence(activity = discord.Activity(name = newgame, type = type, url = url))
        except Exception as error:
                howbownah = await ctx.channel.send("It didn\'t work.")
                killmsg.append(howbownah)
                
                sleepytime = 2
                
                #print (error)
    else:
        howbownah = await ctx.channel.send("You don\'t have permission to use that command!")
        killmsg.append(howbownah)
        
        sleepytime = 3
    
    await asyncio.sleep(sleepytime)
    
    await purgekillmsg(ctx, killmsg)
    
    replyignore = []
        
# Changes the "status" of the bot.
@client.command()
async def change_status(ctx, status):
    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    # Check for perms, then change status as specified.
    if ctx.author.id in [409452148510949408, 469129991544766475]:
        try:
            await client.change_presence(status = discord.Status(status))
        except Exception as error:
            await ctx.channel.send("It didn\'t work.")
            
            print (error)
    else:
        howbownah = await ctx.channel.send("You don\'t have permission to use that command!")
        killmsg.append(howbownah)
        
        # sleepytime here would be 2, but theres's only one instance of error here.

    await asyncio.sleep(2)
    
    await purgekillmsg(ctx, killmsg)
        
# Delete messages in the channel executed (does not iterate)
@client.command()
async def clear(ctx, amount = 10):
    await ctx.message.delete()	# Generic deletion of command executed
    
    amount = int(round(amount))
    # Find the specified number of messages within the channel the command was executed and delete them.
    if ctx.author.id in [409452148510949408, 469129991544766475]:
        if amount > 100:
            amount = 100
        elif amount < 1:
            amount = 1
        
        await ctx.channel.purge(limit = amount)
    else:
        return
        
# Checks *limit* amount of messages in *channel*, and deletes those from *person*.
@client.command()
async def delfromuser(ctx, person, amount = 100, channel = None):
    await ctx.message.delete()	# Generic deletion of command executed.

    # Casting of inputs to integer and getting user from mention.
    amount = int(amount)
    target = client.get_user(int(person[2:-1].replace("!", "")))
    
    # Gets channel (if specified, otherwise it's channel executed in) and deletes messages found by *person*.
    if ctx.author.id in [357943536722903043, 409452148510949408, 469129991544766475]:
        if amount == 1:
            amount = 2
        
        if amount > 100:
            amount = 100
        
        if channel == None:
            channel = ctx.channel
        else:
            channel = client.get_channel(int(channel[2:-1]))
            
        def isTarget(msg):
            return msg.author == target
        
        await channel.purge(limit = int(round(amount)), check = isTarget, bulk = True)
    else:
        return

# Sends a DM from the bot.
@client.command()
async def dm(ctx, person, *stuff):
    await ctx.message.delete()	# Generic deletion of command executed.
    
    # Get user from mention, then sends them a DM of the message.
    if ctx.author.id in [409452148510949408, 469129991544766475]:
        try:
            target = client.get_user(int(person[2:-1].replace("!", "")))
            
            output = ""
            
            for word in stuff:
                output += word
                output += " "
            
            await target.send(output)
        except:
            print("Cannot send DM.")
        
    else:
        return

# Sends a message from the bot in the specified channel.
@client.command()
async def masquerade(ctx, channel, *message):
    await ctx.message.delete()	# Generic deletion of command executed.
    
    # Get channel from ID, then send the message.
    destchannel = client.get_channel(int(channel[2:-1]))
    
    if (ctx.author.id in [409452148510949408, 469129991544766475, 467729503347671050]):
        output = ""
        
        for word in message:
            output += word
            output += " "
        
        await destchannel.send(output)
    else:
        pass

# Count how many messages the person specified has sent.
@client.command()
async def msgcount(ctx, person = ""):
    await ctx.message.delete()	# Generic deletion of command executed.
    
    # Open User logs, and find the number of messages sent within the "messages" entry of the specified person.
    with open('/home/pi/Ezenine/users.json', 'r') as f: 
        users = json.load(f)
            
    if person == "":
        await ctx.send(f"{ctx.author.mention}, your message count is: {str(users[str(ctx.author.id)]['messages'])}")
    else:
        target = client.get_user(int(person[2:-1].replace("!", "")))
        
        if target == ctx.author:	# Check if they mentioned themselves
            await ctx.send(f"{ctx.author.mention}, your message count is: {str(users[str(ctx.author.id)]['messages'])}")
        
        if str(target.id) not in users:	# If this person isn't in the system for some reason
            update_data(users, target, False)
            
            with open('/home/pi/Ezenine/users.json', 'w') as f:
                json.dump(users, f)
        
        await ctx.send(f"{ctx.author.mention}, {target.display_name}\'s message count is: {str(users[str(target.id)]['messages'])}")

# Bans the specified person, DMs the reason, and deletes messages from them going *duration* days back.
@client.command()
async def ban(ctx, person, duration, *reason):
    await ctx.message.delete()	# Generic deletion of command executed.

    # Obtain target from mention, ban them, then DM the reason why. Also deletes messages going back duration days.
    target = client.get_user(int(person[2:-1].replace("!", "")))
    
    if any(entry in ["Perfected Darkness", "Personification of Death"] for entry in [role.name for role in ctx.author.roles]):        
        readablereason = ""
        
        for word in reason:
            readablereason += word
            readablereason += " "
        
        if readablereason == "":
            await target.send(f"You have been banned from {ctx.server}.")
        else:
            await target.send(f"You have been banned from {ctx.server}, the reason being: {readablereason}.")
        
        await ctx.guild.ban(target, reason = readablereason, delete_message_days = int(duration))

        await client.get_channel(505781896014331905).send(f"{ctx.author.mention} has banned {target.mention} via me.")
    else:
        howbownah = await ctx.messages.reply("You don\'t have the authority to ban people!")
        
        await asyncio.sleep(2)
        
        await howbownah.delete()
        
# Kick the specified person and DM them the reason why.
@client.command()
async def kick(ctx, person, *reason):
    await ctx.message.delete()	# Generic deletion of command executed.

    # Obtain target, kick them, then DM them why.
    target = client.get_user(int(person[2:-1].replace("!", "")))
    
    if any(entry in ["Shard of Oblivion", "Perfected Darkness", "Void", "Personification of Death"] for entry in [role.name for role in ctx.author.roles]):        
        readablereason = ""
        
        for word in reason:
            readablereason += word
            readablereason += " "
        
        if readablereason == "":
            await target.send(f"You have been kicked from {ctx.server}.")
        else:
            await target.send(f"You have been kicked from {ctx.server}, the reason being: {readablereason}.")
            
        await ctx.guild.kick(target, reason = readablereason)
        
        await client.get_channel(505781896014331905).send(f"{ctx.author.mention} has kicked {target.mention} via me.")
    else:
        howbownah = await ctx.author.send("You don\'t have the authority to kick people!")
        
        await asyncio.sleep(2)
        
        await howbownah.delete()
           
# Unbans the specified person. 
@client.command()
async def unban(ctx, person, *reason):
    await ctx.message.delete()	# Generic deletion of command executed.
    
    target = client.get_user(int(person[2:-1].replace("!", "")))
    
    if any(entry in ["Shard of Oblivion", "Perfected Darkness", "Personification of Death"] for entry in [role.name for role in ctx.author.roles]):        
        readablereason = ""
        
        for word in reason:
            readablereason += word
            readablereason += " "
            
        await ctx.guild.unban(target, reason = readablereason)

        await client.get_channel(505781896014331905).send(f"{ctx.author.mention} unbanned {target.mention} via me.")

    else:
        howbownah = await ctx.author.send("You don't have the authority to unban people!")
        
        await asyncio.sleep(2)
        
        await howbownah.delete()
        
# Give specified roles to the mentioned person.
@client.command()
async def privilege(ctx, person, *roles):
    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    # Generic DMignore use for ignoring DMs involved in a command.
    global dmignore
    
    # Check for perms, get person from mention, then give them the specified role.
    target = ctx.guild.get_member(int(person[2:-1].replace("!", "")))
    
    rolelist = []
    for role in roles:
        rolelist.append(ctx.guild.get_role(int(role[3:-1])))
    
    if any(entry in ["Shard of Oblivion", "My Diamond Waifu", "Personification of Death"] for entry in [role.name for role in ctx.author.roles]):
        dialog1 = await ctx.author.send("Enter the SAC (Standard Access Code): ")
        killmsg.append(dialog1)
        
        SAC = await client.wait_for("message", check = pm_response(ctx))
        dmignore.append(SAC)
        
        if SAC.content == sac:
             await target.add_roles(*rolelist)
        else:
            howbownah = await ctx.send("Incorrect Access code!")
            killmsg.append(howbownah)
            # sleepytime here would be 2, but all instances of error here use 2.
    else:
        howbownah = await ctx.send("You do not possess the required permissions!")
        killmsg.append(howbownah)
        # sleepytime here would be 2, but all instances of error here use 2.
        
    await asyncio.sleep(2)
    
    await purgekillmsg(ctx, killmsg)
        
    dmignore = []

# Reboot the Raspberry Pi
@client.command()
async def rebootsys(ctx):
    # Setup sleepytime
    sleepytime = 2

    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    # Generic DMignore use for ignoring DMs in a command message.
    global dmignore
    
    # Check for perms, correct MAC, then reboot, or return corresponding error message.
    if "Personification of Death" in [role.name for role in ctx.author.roles]:
        dialog1 = await ctx.author.send("Enter the MAC (Maintenence Code): ")
        killmsg.append(dialog1)
        
        MAC = await client.wait_for("message", check = pm_response(ctx))
        dmignore.append(MAC)
        
        if MAC.content == mac:
            dialog2 = await ctx.author.send("Maintenence Code Accepted. Final confirmation, Y/N: ")
            killmsg.append(dialog2)
            
            confirm = await client.wait_for("message", check = pm_response(ctx))
            dmignore.append(confirm)
            
            if confirm.content.lower() == "y":
                reboot = await ctx.author.send("REBOOTING...")
                killmsg.append(reboot)
                
                await asyncio.sleep(2.5)
                
                await purgekillmsg(ctx, killmsg)
                
                await asyncio.sleep(2.5)
                
                os.system("sync;sync;sudo reboot")
            else:
                cancel = await ctx.author.send("Reboot Cancelled.")
                killmsg.append(cancel)
                
                sleepytime = 2
        else:
            cancel = await ctx.author.send("Maintenence Code Denied. Reboot Cancelled.")
            killmsg.append(cancel)
            
            sleepytime = 3
    else:
        howbownah = await ctx.author.send("You cannot execute this command!")
        killmsg.append(howbownah)
        
        sleepytime = 2
        
    await asyncio.sleep(sleepytime)
    
    await purgekillmsg(ctx, killmsg)
    
    dmignore = []
        
# Remove specified roles from the mentioned person.
@client.command()
async def rescind(ctx, person, *roles):
    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    # Generic DMignore use for ignoring DMs involved in a command.
    global dmignore
    
    # Check for perms, get person from mention, then remove the specified role(s) from them.
    target = ctx.guild.get_member(int(person[2:-1].replace("!", "")))
    
    rolelist = []
    for role in roles:
        rolelist.append(ctx.guild.get_role(int(role[3:-1])))
    
    if any(entry in ["Shard of Oblivion", "My Diamond Waifu", "Personification of Death"] for entry in [role.name for role in ctx.author.roles]):
        dialog1 = await ctx.author.send("Enter the SAC (Standard Access Code): ")
        killmsg.append(dialog1)
        
        SAC = await client.wait_for("message", check = pm_response(ctx))
        dmignore.append(SAC)
        
        if SAC.content == sac:
             await target.remove_roles(*rolelist)
        else:
            howbownah = await ctx.send("Incorrect Access code!")
            killmsg.append(howbownah)
            # sleepytime here would be 2, but all instances of error here use 2.
    else:
        howbownah = await ctx.send("You do not possess the required permissions!")
        killmsg.append(howbownah)
        # sleepytime here would be 2, but all instances of error here use 2.
        
    await asyncio.sleep(2)
    
    await purgekillmsg(ctx, killmsg)
        
    dmignore = []
        
# Chooses a random person within the server and summons them.
@client.command()
async def summon(ctx):
    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    # Check if the person has the proper perms, then chooses a random other person to ping. 
    if ctx.channel.permissions_for(ctx.author).mention_everyone:
        memberList = []
        
        for member in ctx.guild.members:
            if member.bot or ctx.author == member:
                continue
            else:
                memberList.append(member)

        victim = client.get_user(random.choice(memberList).id)
        await ctx.send(f"{victim.mention}! You have been chosen!")
    else:
        howbownah = await ctx.send("You cannot execute this command!")
        killmsg.append(howbownah)
        # sleepytime here would be 2, but theres's only one instance of error here.
    
    await asyncio.sleep(2)
    
    await purgekillmsg(ctx, killmsg)

# Loads a cog
@client.command()
@commands.is_owner()
async def load_cog(ctx, *, cog: str):
    client.load_extension(f"cogs.{cog}")

# Unloads a cog
@client.command()
@commands.is_owner()
async def unload_cog(ctx, *, cog: str):
    client.unload_extension(f"cogs.{cog}")

# Reloads a cog
@client.command()
@commands.is_owner()
async def reload_cog(ctx, *, cog: str):
    client.reload_extension(f"cogs.{cog}")

#endregion Commands

for cog in settings["cogsOnStartup"]:
    client.load_extension(cog)

client.run(settings["token"])