import discord
from discord.ext import commands
import asyncio
import youtube_dl
import random
import json
import os
import logging

logging.basicConfig(level = logging.INFO)

intents = discord.Intents.default()
intents.members = True

client = commands.Bot(command_prefix = ".", intents = intents)

token = "NDc1NDIxOTUxOTM0OTg4Mjg4.DlDZBA.9VlFx9_KqQz_oow6D-3snUtnUL8"

route4message = """You have discovered an ancient way to becoming the fabled Shadenrow, or Shadow Folk. \
Don't tell people how you have got here, otherwise the secrets of the Shadenrow will be forever lost to you. \
You can become Shadenrow only after climbing all other ladders, and your message count will remain locked until then. \
You must amass a total of 9 Million messages to reach Shadenrow status. \
Switching to other paths before reaching Shadenrow resets your message count to 50000. Good Luck."""

sac = "73298462" # Standardized Access Code
mac = "93375B48D6" # Maintenence Access Code
replyignore = []
dmignore = []

players = {}
queues = {}

# Deletes any messages within a hitlist.
async def purgekillmsg(ctx, hitlist):
    for msg in hitlist:
        if msg.channel != ctx.channel:	# Deletes DM messages one by one, and removes them from hitlist.
            await msg.delete()
            hitlist.remove(msg)
    await ctx.channel.delete_messages(hitlist)	# Purges remaining messages.
    
# Might need to change...
def check_queue(id):
    if queues[id] != []:
        player = queues[id].pop[0]
        players[id] = player
        player.start()

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

chat_filter = ["NIGGA", "FAG", "NIGGER"]
bypass_list = [409452148510949408, 469129991544766475]

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
    elif context.valid:	# Commands ignore the rest of the code.
        pass
    elif message in replyignore:
        pass
    else:
        # If it's in the server, contribute to xp system.
        if message.guild.id == 462277524542717973:
            with open('/home/pi/Ezenine/users.json', 'r') as f:
                users = json.load(f)

            await update_data(users, message.author)
            await add_experience(users, message.author, 5)
            await level_up(users, message.author, message.channel)
            await rank_up(users, message.author, message.channel)

            with open('/home/pi/Ezenine/users.json', 'w') as f:
                json.dump(users, f)
        
        # Chat filter
        contents = message.content.split(" ")
        for word in contents:
            if word.upper() in chat_filter:
                if not message.author.id in bypass_list:
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

    await update_data(users, member)
    
    with open('/home/pi/Ezenine/users.json', 'w') as f:
        json.dump(users, f)

@client.event
async def on_member_remove(member):
    await client.get_channel(505781896014331905).send(f"{member.mention} left the server. :(")

@client.event
async def on_member_ban(guild, member):
    await client.get_channel(505781896014331905).send(f"{member.mention} has been banned from the server {guild.name}.")
    
@client.event
async def on_member_unban(guild, member):
    await client.get_channel(505781896014331905).send(f"{member.mention} has been unbanned from the server {guild.name}.")                 

# XP Functions

# Updates the users.json file for a user.
async def update_data(users, user):
    if not str(user.id) in users:	# If a user is not present in the list, make an entry for them.
        users[str(user.id)] = {}
        users[str(user.id)]["name"] = user.name
        try:
            users[str(user.id)]["nickname"] = user.nick
        except Exception:
            pass
        users[str(user.id)]["experience"] = 0
        users[str(user.id)]["level"] = 1
        users[str(user.id)]["messages"] = 0
        users[str(user.id)]["mcountlocked"] = 0
        users[str(user.id)]["route"] = 0
    else:
        # If they are, count messages if mcount isn't locked, and update whether it should be locked.
        if not users[str(user.id)]["mcountlocked"]:
            users[str(user.id)]["messages"] += 1
            
        if "Wisp of Darkness" in [role.name for role in user.roles]:
            users[str(user.id)]["mcountlocked"] = 1
        else:
            users[str(user.id)]["mcountlocked"] = 0

# Increments a user's exp.
async def add_experience(users, user, exp):
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
    route = users[str(user.id)]["route"]
    
    if route == 1:
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
            role = discord.utils.get(user.guild.roles, name = "Penumbral")
            
            await user.add_roles(role)
    elif route == 2:
        if messages == 666666:
            role1 = discord.utils.get(user.guild.roles, name = "El Diablo")
            role2 = discord.utils.get(user.guild.roles, name = "Corrupt Demon Spawn")
            roles[roles.index(role2)] = role1
            
            await user.edit(roles)
        elif messages == 475000:
            role1 = discord.utils.get(user.guild.roles, name = "Corrupt Demon Spawn")
            role2 = discord.utils.get(user.guild.roles, name = "Draconic")
            roles[roles.index(role2)] = role1
            
            await user.edit(roles)
        elif messages == 275050:
            role1 = discord.utils.get(user.guild.roles, name = "Draconic")
            role2 = discord.utils.get(user.guild.roles, name = "Follower of Flame")
            roles[roles.index(role2)] = role1
            
            await user.edit(roles)
        elif messages == 100000:
            role = discord.utils.get(user.guild.roles, name = "Follower of Flame")
            
            await user.add_roles(role)
    elif route == 3:
        if messages == 1000000:
            role1 = discord.utils.get(user.guild.roles, name = "Pefected Darkness")
            role2 = discord.utils.get(user.guild.roles, name = "Void")
            roles[roles.index(role2)] = role1
            
            await user.edit(roles)
        elif messages == 500000:
            role1 = discord.utils.get(user.guild.roles, name = "Void")
            role2 = discord.utils.get(user.guild.roles, name = "Shadow")
            roles[roles.index(role2)] = role1
            
            await user.edit(roles)
        elif messages == 175000:
            role = discord.utils.get(user.guild.roles, name = "Shadow")
            
            await user.add_roles(role)
    elif route == 4:
        if messages == 9000000:
            role = discord.utils.get(user.guild.roles, name = "Shadenrow")
            
            await user.add_roles(role)
    elif route == 0:
        if messages == 50000:
            role1 = discord.utils.get(user.guild.roles, name = "Wisp of Death")
            role2 = discord.utils.get(user.guild.roles, name = "Blossoming Darkness")
            roles[roles.index(role2)] = role1
            
            await user.edit(roles)
            
            users[str(user.id)]["mcountlocked"] = 1
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

# COMMANDS

# A simple ping command (latency later)
@client.command()
async def ping(ctx):
    await ctx.send(f"Pong! {client.latency * 1000}ms")

# A simple echoing command
@client.command()
async def echo(ctx, *args):
    await ctx.message.delete()	# Generic deletion of command executed
    
    output = ""
    for word in args:
        output += word
        output += " "
    await ctx.send(output)

# Delete messages in the channel executed (does not iterate)
@client.command()
async def clear(ctx, amount = 10):
    await ctx.message.delete()	# Generic deletion of command executed
    
    # Find the specified number of messages within the channel the command was executed and delete them.
    if ctx.author.id in [409452148510949408, 469129991544766475]:
        if amount > 100:
            amount = 100
        
        await ctx.channel.purge(limit = int(round(amount)))
    else:
        return
        
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
            await update_data(users, target)
            
            with open('/home/pi/Ezenine/users.json', 'w') as f:
                json.dump(users, f)
        
        await ctx.send(f"{ctx.author.mention}, {target.display_name}\'s message count is: {str(users[str(target.id)]['messages'])}")

# Choose branch of roles to continue to.
@client.command()
async def route(ctx, route = 0, confirm = 0):
    await ctx.message.delete() # Generic deletion of command executed

    if "Wisp of Darkness" in [role.name for role in ctx.author.roles]:
        if not confirm:	# Display info if confirm is 0
            await ctx.send("This resets your progress on a route if you are switching routes, but does not if you completed it, and you lose all roles associated with that route! Execute the command like this to continue: `.route <route> 1`")
        
        if confirm and int(route) in [1, 2, 3]:
            try:
                # Open User info, and either changes route, resetting if not completed, or enters a route.
                with open('/home/pi/Ezenine/users.json', 'r') as f:
                    users = json.load(f)
                
                if (int(route) == 1 and "Total Darkness" in [role.name for role in ctx.author.roles]) or \
                   (int(route) == 2 and "El Diablo" in [role.name for role in ctx.author.roles]) or \
                   (int(route) == 3 and "Perfected Darkness" in [role.name for role in ctx.author.roles]):
                    users[ctx.author.id]["route"] = route
                    users[ctx.author.id]["mcountlocked"] = 0
                    users[ctx.author.id]["messages"] = 50000
                elif int(route) == 3 and ("Total Darkness" not in [role.name for role in ctx.author.roles] or "El Diablo" not in [role.name for role in ctx.author.roles]):
                    ctx.send("You must have conquered the merging with Darkness, and survived the depths of Hell. (Must have done routes 1 & 2)")
                else:
                    users[ctx.author.id]["route"] = route
                    users[ctx.author.id]["mcountlocked"] = 0
                    users[ctx.author.id]["messages"] = 50000
                    
                    role1 = discord.utils.get(ctx.guild.roles, name = "Shadow")
                    role2 = discord.utils.get(ctx.guild.roles, name = "Void")
                    role3 = discord.utils.get(ctx.guild.roles, name = "Perfected Darkness")
                    role4 = discord.utils.get(ctx.guild.roles, name = "El Diablo")
                    role5 = discord.utils.get(ctx.guild.roles, name = "Corrupt Demon Spawn")
                    role6 = discord.utils.get(ctx.guild.roles, name = "Draconic")
                    role7 = discord.utils.get(ctx.guild.roles, name = "Follower of Flame")
                    role8 = discord.utils.get(ctx.guild.roles, name = "Total Darkness")
                    role9 = discord.utils.get(ctx.guild.roles, name = "Umbral")
                    role10 = discord.utils.get(ctx.guild.roles, name = "Penumbral")                
                    
                    await ctx.author.remove_roles(role1, role2, role3, role4, role5, role6, role7, role8, role9, role10)
                
                with open('/home/pi/Ezenine/users.json', 'w') as f:
                    json.dump(users, f)
            except:
                pass
        elif route == 0:	# Displays info when executed w/o specifications.
            await ctx.send("Choose a route: 1 for One with Darkness (OwD), 2 for Hell route, and 3 for Authority route.")
        elif route == 4:	# Shadenrow Code, check for max role on routes 1-3, then proceeds.
            with open('/home/pi/Ezenine/users.json', 'r') as f:
                    users = json.load(f)
            
            if all(entry in ["Total Darkness", "El Diablo", "Perfected Darkness"] for entry in [role.name for role in ctx.author.roles]):    
                users[ctx.author.id]["route"] = route
                users[ctx.author.id]["mcountlocked"] = 0
            else:
                pass
            
            with open('/home/pi/Ezenine/users.json', 'w') as f:
                    json.dump(users, f)
            
            await ctx.author.send(route4message)
    else:
        await ctx.send("You must have reached the Wisp of Death state to specialize your form!")

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
            
# Leave command. Check back on.
@client.command()
async def leave(ctx):
    await ctx.message.delete()	# Generic deletion of command executed.

    if "DJ" in [role.name for role in ctx.author.roles]:
        try:
            voice_client = client.voice_client_in(ctx.guild)
            
            await voice_client.disconnect()
        except Exception:
            dialog1 = await ctx.channel.send("There must be a voice channel for me to leave.")
            
            await asyncio.sleep(2)
            
            await dialog1.delete()
            
    else:
        dialog2 = await ctx.channel.send("You don\'t have permission to use that command!")
        
        await asyncio.sleep(2)
        
        await dialog2.delete()
        
# Play command. Check back on.
@client.command()
async def play(ctx, url):
    try:
        try:
            if not client.is_voice_connected(ctx.guild):
                voice_channel = ctx.author.voice.voice_channel
                
                await client.join_voice_channel(voice_channel)
        except Exception as error:
            print (error)
            
            await ctx.channel.send("You must be in a voice channel in the server for me to play a song.")
        
        if players[ctx.guild.id].is_playing():
            voice_client = client.voice_client_in(ctx.guild)
            
            player = await voice_client.create_ytdl_player(url, after = lambda: check_queue(ctx.guild.id))
            
            if ctx.guild.id in queues:
                queues[ctx.guild.id].append(player)
            else:
                queues[ctx.guild.id] = [player]
            
            await ctx.channel.send("Song queued.")
            await ctx.channel.send(url)
        else:            
            voice_client = client.voice_client_in(ctx.guild)
            
            player = await voice_client.create_ytdl_player(url, after = lambda: check_queue(ctx.guild.id))
            
            players[ctx.guild.id] = player
            
            player.start()
            
            await ctx.channel.send("Song started.")
            await ctx.channel.send(url)
    except:
        voice_client = client.voice_client_in(ctx.guild)
        
        player = await voice_client.create_ytdl_player(url, after = lambda: check_queue(ctx.guild.id))
        
        players[ctx.guild.id] = player
        
        player.start()
        
        await ctx.channel.send("Song Queued.")
        await ctx.channel.send(url)

# Pause command. Check back on.
@client.command()
async def pause(ctx):
    await ctx.message.delete()	# Generic deletion of command executed.

    if "DJ" in [role.name for role in ctx.author.roles]:
        players[ctx.guild.id].pause()
    else:
        dialog1 = await ctx.channel.send("You don\'t have permission to use that command!")
        await asyncio.sleep(2)
        await dialog1.delete()
    
# Stop command. Check back on.
@client.command()
async def stop(ctx):
    await ctx.message.delete()	# Generic deletion of command executed.

    if "DJ" in [role.name for role in ctx.author.roles]:
        players[ctx.guild.id].stop()
    else:
        dialog1 = await ctx.channel.send("You don\'t have permission to use that command!")
        await asyncio.sleep(2)
        await dialog1.delete()
    
# Resume command. Check back on.
@client.command()
async def resume(ctx):
    await ctx.message.delete()	# Generic deletion of command executed.

    if "DJ" in [role.name for role in ctx.author.roles]:
        id = ctx.guild.id
        players[id].resume()
    else:
        dialog1 = await ctx.channel.send("You don\'t have permission to use that command!")
        
        await asyncio.sleep(2)
        await dialog1.delete()
        
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
#        try:
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
#     except Exception as error:
#             howbownah = await ctx.channel.send("It didn\'t work.")
#             killmsg.append(howbownah)
#             
#             sleepytime = 2
#             
#             #print (error)
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


# Dungeons and Dragons code
        
xpthresholds = {1:[25, 50, 75, 100], 2:[50, 100, 150, 200], 3:[75, 150, 225, 400], 4:[125, 250, 375, 500], 5:[250, 500, 750, 1100],\
                6:[300, 600, 900, 1400], 7:[350, 750, 1100, 1700], 8:[450, 900, 1400, 2100], 9:[550, 1100, 1600, 2400], 10:[600, 1200, 1900, 2800],\
                11:[800, 1600, 2400, 3600], 12:[1000, 2000, 3000, 4500], 13:[1100, 2200, 3400, 5100], 14:[1250, 2500, 3800, 5700], 15:[1400, 2800, 3800, 5700],
                16:[1600, 3200, 4800, 7200], 17:[2000, 3900, 5900, 8800], 18:[2100, 4200, 6300, 9500], 19:[2400, 4900, 7300, 10900], 20:[2800, 5700, 8500, 12700]}

# Roll a dice, specified in NdN format, plus a constant if specified.
@client.command()
async def roll(ctx, dice : str, constant = 0):
    # Cast inputs to integers.
    constant = int(constant)
    try:
        rolls, limit = map(int, dice.split("d"))
    except Exception:
        if ValueError:
            rolls = 1
            limit = int(dice.split("d")[1])
        else:
            await ctx.send("Format has to be in NdN!")
            return
    
    # Generate a number from 1 to *limit* *rolls* times, sum them, add constant if needed, then output.
    numbers = []
    
    for r in range(rolls):
        numbers.append(random.randint(1, limit))
    
    result = str(numbers)[1:-1].replace(", ", "+")
    total = sum(numbers)

    if constant != 0:
        total = str(total + constant)
        await ctx.send(f"{ctx.author.mention}: `{ctx.message.content[6:]}` ({result}) + {constant}  =  {total}")
    else:
        total = str(total)
        await ctx.send(f"{ctx.author.mention}: `{ctx.message.content[6:]}` ({result})  =  {total}")

# D&D thing. Soon to be a cog, and prob needs to be split up.
@client.command()
async def DnD(ctx):
    # Generic Reply Ignore use for message processing.
    global replyignore
    
    # Generic Killmsg use for deletion of multiple messages.
    killmsg = []
    killmsg.append(ctx.message)
    
    subsections = ["char sheets", "encounter", "monsters", "classes", "races", "backgrounds", "items", "weapons", "armor", "shields", "rules"]
    
    dialog1 = await ctx.send(f"What would you like to create or modify? Valid choices include: {str(subsections)[1:-1].replace(',', '').upper()}")
    killmsg.append(dialog1)
    
    subsection = await client.wait_for("message", check = response(ctx))
    replyignore.append(subsection)
    killmsg.append(subsection)
    
    if subsection.content.lower() in subsections:
        if subsection.content.lower() == "char sheets":
            del subsection.content
            
            dialog2 = await ctx.send("Options to use include are: `save` to update an entry of a session, `load` a previously saved session, or `new` to create a new entry. Type `cancel` to exit. In the case yhou need to delete a previously made entry, use `delete`.")
            killmsg.append(dialog2)
            
            mode = await client.wait_for("message", check = response(ctx))
            replyignore.append(mode)
            killmsg.append(mode)
            
            options = ["load", "new", "cancel", "save", "delete"]
            
            done = False
            
            while done == False and mode.content.lower() != "":
                if mode.content.lower() == "save":
                    del mode.content
                    
                    with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                        sessions = json.load(f)
                    
                    dialog3 = await ctx.send("Please enter your session id: ")
                    killmsg.append(dialog3)
                    
                    reqsessionid = await client.wait_for("message", check = response(ctx))
                    replyignore.append(reqsessionid)
                    killmsg.append(reqsessionid)
                    
                    dialog4 = await ctx.send("Is this your session?")
                    killmsg.append(dialog4)
                    
                    confirmation = await ctx.author.send(sessions[reqsessionid.content])
                    killmsg.append(confirmation)
                    
                    if confirmation.content.lower() in ["yes", "y"]:
                        dialog5 = await ctx.send("What character would you like to modify?")
                        killmsg.append(dialog5)
                        
                        modify = await client.wait_for("message", check = response(ctx))
                        replyignore.append(modify)
                        killmsg.append(modify)
                        
                        if int(modify.content) <= int(sessions[reqsessionid]["Number of Players: "]):
                            dialog6 = await ctx.send(f"Enter the player{modify.content}\'s character: ")
                            killmsg.append(dialog6)
                            
                            entry = await client.wait_for("message", check = response(ctx))
                            replyignore.append(entry)
                            killmsg.append(entry)
                            
                            sessions[reqsessionid]["Description of Players: "] = entry.content
                            
                            with open('/home/pi/Ezenine/dnd.json', 'w') as f:
                                json.dump(sessions, f)
                            
                            dialog7 = await ctx.send("Your session has been successfully saved!")
                            killmsg.append(dialog7)
                    else:
                        dialog8 = await ctx.send("Session edit canceled.")
                        killmsg.append(dialog8)
                        
                    done = True
                elif mode.content.lower() == "new":
                    del mode.content
                    
                    with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                        sessions = json.load(f)
                    
                    dialog9 = await ctx.send("Enter number of players: ")
                    killmsg.append(dialog9)
                    
                    plnum = await client.wait_for("message", check = response(ctx)) # Number of players
                    replyignore(plnum)
                    killmsg.append(plnum)
                    
                    pldes = [] # Description of players
                    
                    # Ask for description of each player then append to pldes
                    for player in range(int(plnum.content)):
                        dialog = await ctx.send(f"Enter the player{player + 1}\'s character: ")
                        killmsg.append(dialog)
                        
                        entry = await client.wait_for("message", check = response(ctx))
                        replyignore.append(entry)
                        killmsg.append(entry)
                        
                        
                        pldes.append(entry.content)
                    
                    currsession = {"Number of Players: ": plnum.content, "Description of Players: ": pldes, "DM: ": ctx.author.name}
                    
                    # Null mechanic. Deleting a session currently replaces it with null to keep indexes the same. Need to fix.
                    fns = False
                    nsindex = 0
                    
                    for session in range(len(sessions)):
                        if session["null"] == "null":
                            fns = True # Found null session
                            nsindex = sessions.index(session) # Null session index
                            break
                    
                    if not fns:
                        sessions.append(currsession)
                    else:
                        sessions[nsindex] = currsession
                    # Null mechanic end.
                    
                    dialog10 = await ctx.send(f"Your session id is: {str(sessions.index(currsession))}")
                    killmsg.append(dialog10)
                    
                    with open('/home/pi/Ezenine/dnd.json', 'w') as f:
                        json.dump(sessions, f)
                    
                    done = True
                elif mode.content.lower() == "load":
                    del mode.content
                    
                    dialog11 = await ctx.send("Enter your session id please: ")
                    killmsg.append(dialog11)
                    
                    id = await client.wait_for("message", check = response(ctx))
                    replyignore.append(id)
                    killmsg.append(id)
                    
                    with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                        sessions = json.load(f)
                    
                    await ctx.author.send(f"Loading session #{id.content}: Just a sec...")
                    
                    await asyncio.sleep(2)
                    
                    await ctx.author.send(f"Author: {sessions[int(id.content)]['DM: ']}\nNumber of Players: {sessions[int(id.content)]['Number of Players: ']}\nDescriptions: ")
                
                    for players in range(int(sessions[int(id.content)]["Number of Players: "])):
                        await ctx.author.send(sessions[int(id.content)]["Description of Players: "][players])
                    
                    done = True
                elif mode.content.lower() == "delete":
                    del mode.content
                    
                    dialog12 = await ctx.send("What is your session id?")
                    killmsg.append(dialog12)
                    
                    session = await client.wait_for("message", check = response(ctx))
                    replyignore.append(session)
                    killmsg.append(session)
                    
                    with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                        sessions = json.load(f)
                    
                    if ctx.author.name == sessions[int(session.content)]["DM: "]:
                        await ctx.author.send(f"If this was your desired session to delete, continue.\nNumber of Players: {sessions[int(session.content)]['Number of Players: ']}\nDescriptions: ")
                        
                        for players in range(int(sessions[int(session.content)]["Number of Players: "])):
                            await ctx.author.send(sessions[int(session.content)]["Description of Players: "][players])
                            await ctx.author.send("-------------------------------------------")
                        
                        dialog13 = await ctx.send("Are you sure?")
                        killmsg.append(dialog13)
                        
                        confirm = await client.wait_for("message", check = response(ctx))
                        replyignore.append(confirm)
                        killmsg.append(confirm)
                        
                        if confirm.content.lower in ["yes", "y"]:
                            # Currently just adds a null field with value null, keeping the number of sessions the same, so other's indices are the same. Need to change.
                            sessions[int(session.content)]["null"] = "null"
                            
                            with open('/home/pi/Ezenine/dnd.json', 'w') as f:
                                json.dump(sessions, f)
                    
                    done = True
                elif mode.content.lower() == "cancel":
                    del mode.content
                    
                    done = True
                else:
                    del mode.content
                    
                    done = True
        elif subsection.content.lower() == "encounter":
            dialog2 = await ctx.send("How many party members are playing?")
            killmsg.append(dialog2)
            
            dialog3 = await client.wait_for("message", check = response(ctx))
            replyignore(dialog3)
            killmsg.append(dialog3)
            
            dialog4 = await ctx.send("How many monsters are there?")
            killmsg.append(dialog4)
            
            dialog5 = await client.wait_for("message", check = response(ctx))
            replyignore.append(dialog5)
            killmsg.append(dialog5)
            
            if int(dialog5.content) == 1:
                dialog6 = await ctx.send("What does the monster\'s xp total to?")
            else:
                dialog6 = await ctx.send("What do the monsters\' xp total to?")
            killmsg.append(dialog6)
            
            dialog7 = await client.wait_for("message", check = response(ctx))
            replyignore.append(dialog7)
            killmsg.append(dialog7)
              
            easythreshold = 0
            mediumthreshold = 0
            hardthreshold = 0
            deadlythreshold = 0
            
            for member in range(int(dialog3.content)):
                dialog = await ctx.send(f"What level is player {member + 1}? (Order doesn\'t matter.)")
                killmsg.append(dialog)
                
                answer = await client.wait_for("message", check = response(ctx))
                replyignore.append(answer)
                killmsg.append(answer)
                
                easythreshold += xpthresholds[int(answer.content)][0]
                mediumthreshold += xpthresholds[int(answer.content)][1]
                hardthreshold += xpthresholds[int(answer.content)][2]
                deadlythreshold += xpthresholds[int(answer.content)][3]
                
            # mxpthreshold = monster experience point threshold
            mxpthreshold = 0
            
            if int(dialog3.content) < 3:
                if int(dialog5.content) == 1:
                    mxpthreshold = int(dialog7.content)*1.5
                elif int(dialog5.content) == 2:
                    mxpthreshold = int(dialog7.content)*2
                elif int(dialog5.content) >= 3 and int(dialog5.content) <= 6:
                    mxpthreshold = int(dialog7.content)*2.5
                elif int(dialog5.content) >= 7 and int(dialog5.content) <= 10:
                    mxpthreshold = int(dialog7.content)*3
                elif int(dialog5.content) >= 11 and int(dialog5.content) <= 14:
                    mxpthreshold = int(dialog7.content)*4
                elif int(dialog5.content) >= 15:
                    mxpthreshold = int(dialog7.content)*5
            elif int(dialog3.content) >= 3 and int(dialog3.content) <= 5:
                if int(dialog5.content) == 1:
                    mxpthreshold = int(dialog7.content)
                elif int(dialog5.content) == 2:
                    mxpthreshold = int(dialog7.content)*1.5
                elif int(dialog5.content) >= 3 and int(dialog5.content) <= 6:
                    mxpthreshold = int(dialog7.content)*2
                elif int(dialog5.content) >= 7 and int(dialog5.content) <= 10:
                    mxpthreshold = int(dialog7.content)*2.5
                elif int(dialog5.content) >= 11 and int(dialog5.content) <= 14:
                    mxpthreshold = int(dialog7.content)*3
                elif int(dialog5.content) >= 15:
                    mxpthreshold = int(dialog7.content)*4    
            elif int(dialog3.content) >= 6:
                if int(dialog5.contnet) == 1:
                    mxpthreshold = int(dialog7.content)*.5
                elif int(dialog5.content) == 2:
                    mxpthreshold = int(dialog7.content)
                elif int(dialog5.content) >= 3 and int(dialog5.content) <= 6:
                    mxpthreshold = int(dialog7.content)*1.5
                elif int(dialog5.content) >= 7 and int(dialog5.content) <= 10:
                    mxpthreshold = int(dialog7.content)*2
                elif int(dialog5.content) >= 11 and int(dialog5.content) <= 14:
                    mxpthreshold = int(dialog7.content)*2.5
                elif int(dialog5.content) >= 15:
                    mxpthreshold = int(dialog7.content)*3
            
            if mxpthreshold >= mediumthreshold and mxpthreshold < hardthreshold:
                dialog8 = await ctx.send("The encounter specified has a medium difficulty.")
                killmsg.append(dialog8)
            elif mxpthreshold >= hardthreshold and mxpthreshold < deadlythreshold:
                dialog8 = await ctx.send("The encounter specified has a hard difficulty.")
                killmsg.append(dialog8)
            elif mxpthreshold >= deadlythreshold:
                dialog8 = await ctx.send("The encounter specified has a deadly difficulty.")
                killmsg.append(dialog8)
            else:
                dialog8 = await ctx.send("The encounter specified has an easy difficulty.")
                killmsg.append(dialog8)
                
            dialog9 = await ctx.send(f"Your party\'s thresholds are, easy difficulty: {easythreshold}, medium difficulty: {mediumthreshold}, hard difficulty, {hardthreshold}, deadly difficulty: {deadlythreshold}.")
    
    await asyncio.sleep(5)
    
    await purgekillmsg(ctx, killmsg)
    
    replyignore = []

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

client.run(token)