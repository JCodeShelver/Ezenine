import discord
from discord.ext import commands
import asyncio
import json
import random


class DnD(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.xpthresholds = {1:[25, 50, 75, 100], 2:[50, 100, 150, 200], 3:[75, 150, 225, 400], 4:[125, 250, 375, 500], 5:[250, 500, 750, 1100],\
                6:[300, 600, 900, 1400], 7:[350, 750, 1100, 1700], 8:[450, 900, 1400, 2100], 9:[550, 1100, 1600, 2400], 10:[600, 1200, 1900, 2800],\
                11:[800, 1600, 2400, 3600], 12:[1000, 2000, 3000, 4500], 13:[1100, 2200, 3400, 5100], 14:[1250, 2500, 3800, 5700], 15:[1400, 2800, 3800, 5700],
                16:[1600, 3200, 4800, 7200], 17:[2000, 3900, 5900, 8800], 18:[2100, 4200, 6300, 9500], 19:[2400, 4900, 7300, 10900], 20:[2800, 5700, 8500, 12700]}

    # Predicates, one for checking if the message is same author, same channel, the other is for same author, in the DMs
    def response(self, ctx):
        def pred(newmsg):
            return newmsg.author == ctx.author and newmsg.channel == ctx.channel
        return pred

    def pm_response(self, ctx):
        def pred(newmsg):
            return newmsg.author == ctx.author and newmsg.channel.type == discord.ChannelType.private
        return pred

    # Deletes any messages within a hitlist.
    async def purgekillmsg(self, ctx, hitlist):
        for msg in hitlist:
            if msg.channel != ctx.channel:	# Deletes DM messages one by one, and removes them from hitlist.
                await msg.delete()
                hitlist.remove(msg)
        await ctx.channel.delete_messages(hitlist)	# Purges remaining messages.

    # Roll a dice, specified in NdN format, plus a constant if specified.
    @commands.command()
    async def roll(self, ctx, dice : str, constant = 0):
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

    # Character Sheet Manager
    @commands.command()
    async def cSheetMgr(self, ctx):
        replyignore = []

        killmsg = []
        killmsg.append(ctx.message)

        async def findSID(reqSID, sessions):
            sIndex = -1

            for index in range(len(sessions)):
                if sessions[index]["ID: "] == reqSID:
                    if sessions[index]["DM: "] == ctx.author.name:
                        sIndex = index
                        break
                    else:
                        await ctx.send("The requested session was not made by you!")
                
                if index + 1 == len(sessions):
                    await ctx.send("The requested ID is not associated to any sessions.")

            return sIndex
        
        options = await ctx.send("Options to use include are: `save` to update an entry of a session, `load` a previously saved session, or `new` to create a new entry. Type `cancel` to exit. In the case yhou need to delete a previously made entry, use `delete`.")
        killmsg.append(options)
        
        mode = await self.client.wait_for("message", check = self.response(ctx))
        replyignore.append(mode)
        killmsg.append(mode)
                                        
        if mode.content.lower() == "save":                        
            with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                sessions = json.load(f)
            
            botmsg = await ctx.send("Please enter your session id: ")
            killmsg.append(botmsg)
            
            reqSID = await self.client.wait_for("message", check = self.response(ctx))
            replyignore.append(reqSID)
            killmsg.append(reqSID)
            
            sIndex = await findSID(reqSID.content, sessions)
            
            if sIndex != -1:
                botmsg = await ctx.send("Is this your session?")
                killmsg.append(botmsg)

                confirmation = await ctx.author.send(sessions[sIndex])
                killmsg.append(confirmation)
                
                if confirmation.content.lower() in ["yes", "y"]:
                    botmsg = await ctx.send("What character would you like to modify?")
                    killmsg.append(botmsg)
                    
                    modify = await self.client.wait_for("message", check = self.response(ctx))
                    replyignore.append(modify)
                    killmsg.append(modify)
                    
                    if int(modify.content) <= int(sessions[sIndex]["Number of Players: "]):
                        botmsg = await ctx.send(f"Enter player {modify.content}\'s character: ")
                        killmsg.append(botmsg)
                        
                        entry = await self.client.wait_for("message", check = self.response(ctx))
                        replyignore.append(entry)
                        killmsg.append(entry)
                        
                        sessions[sIndex]["Description of Players: "][int(modify.content)] = entry.content
                        
                        with open('/home/pi/Ezenine/dnd.json', 'w') as f:
                            json.dump(sessions, f)
                        
                        botmsg = await ctx.send("Your session has been successfully saved!")
                        killmsg.append(botmsg)
                else:
                    botmsg = await ctx.send("Session edit canceled.")
                    killmsg.append(botmsg)

        elif mode.content.lower() == "new":                        
            with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                sessions = json.load(f)
            
            botmsg = await ctx.send("Enter the name/number of your session (you need this to access it in the future): ")
            killmsg.append(botmsg)

            SID = await self.client.wait_for ("message", check = self.response(ctx)) # Session ID
            replyignore.append(SID)
            killmsg.append(SID)
            
            botmsg = await ctx.send("Enter the number of players: ")
            killmsg.append(botmsg)
            
            plnum = await self.client.wait_for("message", check = self.response(ctx)) # Number of players
            replyignore.append(plnum)
            killmsg.append(plnum)
            
            pldes = [] # Description of players
            
            # Ask for description of each player then append to pldes
            for player in range(int(plnum.content)):
                botmsg = await ctx.send(f"Enter the player{player + 1}\'s character: ")
                killmsg.append(botmsg)
                
                entry = await self.client.wait_for("message", check = self.response(ctx))
                replyignore.append(entry)
                killmsg.append(entry)
                
                pldes.append(entry.content)
            
            currsession = {"Number of Players: ": plnum.content, 
                            "Description of Players: ": pldes, 
                            "DM: ": ctx.author.name, 
                            "ID: ": SID.content}
            sessions.append(currsession)

            with open('/home/pi/Ezenine/dnd.json', 'w') as f:
                json.dump(sessions, f)

            botmsg = await ctx.send("Your session has been created!")
            killmsg.append(botmsg)
            
        elif mode.content.lower() == "load":                        
            with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                sessions = json.load(f)
            
            botmsg = await ctx.send("Enter your session id please: ")
            killmsg.append(botmsg)
            
            SID = await self.client.wait_for("message", check = self.response(ctx))
            replyignore.append(SID)
            killmsg.append(SID)

            sIndex = await findSID(SID.content, sessions)
            
            if sIndex != -1:
                session = f"Number of Players: {sessions[sIndex]['Number of Players: ']}\nDescriptions:\n"
                    
                for player in range(int(sessions[sIndex]["Number of Players: "])):
                    session += f"{sessions[sIndex]['Description of Players: '][player]}\n\n"

                await ctx.author.send(session)

        elif mode.content.lower() == "delete":
            with open('/home/pi/Ezenine/dnd.json', 'r') as f:
                sessions = json.load(f)
            
            botmsg = await ctx.send("What is your session id?")
            killmsg.append(botmsg)
            
            session = await self.client.wait_for("message", check = self.response(ctx))
            replyignore.append(session)
            killmsg.append(session)

            sIndex = await findSID(session.content, sessions)
            
            if sIndex != -1:
                if ctx.author.name == sessions[sIndex]["DM: "]:
                    seshconfirm = f"Number of Players: {sessions[sIndex]['Number of Players: ']}\nDescriptions: \n"
                    
                    for player in range(int(sessions[sIndex]["Number of Players: "])):
                        seshconfirm += f"{sessions[sIndex]['Description of Players: '][player]}\n\n"

                    botmsg = await ctx.author.send(seshconfirm)
                    killmsg.append(botmsg)

                    botmsg = await ctx.send("Is this the session you wished to delete?")
                    killmsg.append(botmsg)
                    
                    confirm = await self.client.wait_for("message", check = self.response(ctx))
                    replyignore.append(confirm)
                    killmsg.append(confirm)
                    
                    if confirm.content.lower() in ["yes", "y"]:
                        sessions.pop(sIndex)
                        
                        with open('/home/pi/Ezenine/dnd.json', 'w') as f:
                            json.dump(sessions, f)
                        
                        botmsg = await ctx.send("Your session has been successfully p u r g e d.")
                        killmsg.append(botmsg)

        elif mode.content.lower() == "cancel":                        
            pass
        else:                        
            pass

        await asyncio.sleep(2)
        
        await self.purgekillmsg(ctx, killmsg)
        
    # DnD command (In progress of splitting up.)
    @commands.command()
    async def DnD(self, ctx):
        replyignore = []

        # Generic Killmsg use for deletion of multiple messages.
        killmsg = []
        killmsg.append(ctx.message)
        
        async def findSID(reqSID, sessions):
            sIndex = -1
            for index in sessions:
                if sessions[index]["ID: "] == reqSID.content:
                    if sessions[index]["DM: "] == ctx.author:
                        sIndex = index
                        break
                    else:
                        await ctx.send("The requested session was not made by you!")
                else:
                    await ctx.send("The requested ID is not associated to any sessions.")
            return sIndex

        subsections = ["`encounter`", "`monsters`", "`classes`", "`races`", "`backgrounds`", "`items`", "`weapons`", "`armor`", "`shields`", "`rules`"]
        
        dialog1 = await ctx.send(f"What would you like to create or modify? Valid choices include: {str(subsections)[1:-1].replace(',', '').upper()}")
        killmsg.append(dialog1)
        
        subsection = await self.client.wait_for("message", check = self.response(ctx))
        replyignore.append(subsection)
        killmsg.append(subsection)
        
        if subsection.content.lower() in subsections:                
            if subsection.content.lower() == "encounter":
                dialog2 = await ctx.send("How many party members are playing?")
                killmsg.append(dialog2)
                
                dialog3 = await self.client.wait_for("message", check = self.response(ctx))
                replyignore(dialog3)
                killmsg.append(dialog3)
                
                dialog4 = await ctx.send("How many monsters are there?")
                killmsg.append(dialog4)
                
                dialog5 = await self.client.wait_for("message", check = self.response(ctx))
                replyignore.append(dialog5)
                killmsg.append(dialog5)
                
                if int(dialog5.content) == 1:
                    dialog6 = await ctx.send("What does the monster\'s xp total to?")
                else:
                    dialog6 = await ctx.send("What do the monsters\' xp total to?")
                killmsg.append(dialog6)
                
                dialog7 = await self.client.wait_for("message", check = self.response(ctx))
                replyignore.append(dialog7)
                killmsg.append(dialog7)
                
                easythreshold = 0
                mediumthreshold = 0
                hardthreshold = 0
                deadlythreshold = 0
                
                for member in range(int(dialog3.content)):
                    dialog = await ctx.send(f"What level is player {member + 1}? (Order doesn\'t matter.)")
                    killmsg.append(dialog)
                    
                    answer = await self.client.wait_for("message", check = self.response(ctx))
                    replyignore.append(answer)
                    killmsg.append(answer)
                    
                    easythreshold += self.xpthresholds[int(answer.content)][0]
                    mediumthreshold += self.xpthresholds[int(answer.content)][1]
                    hardthreshold += self.xpthresholds[int(answer.content)][2]
                    deadlythreshold += self.xpthresholds[int(answer.content)][3]
                    
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
        
        await self.purgekillmsg(ctx, killmsg)
        
        replyignore = []

def setup(client):
    client.add_cog(DnD(client))