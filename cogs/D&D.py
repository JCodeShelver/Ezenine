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

    # D&D thing that probably should be split up.
    @commands.command()
    async def DnD(self, ctx):
        replyignore = []

        # Generic Killmsg use for deletion of multiple messages.
        killmsg = []
        killmsg.append(ctx.message)
        
        subsections = ["char sheets", "encounter", "monsters", "classes", "races", "backgrounds", "items", "weapons", "armor", "shields", "rules"]
        
        dialog1 = await ctx.send(f"What would you like to create or modify? Valid choices include: {str(subsections)[1:-1].replace(',', '').upper()}")
        killmsg.append(dialog1)
        
        subsection = await self.client.wait_for("message", check = self.response(ctx))
        replyignore.append(subsection)
        killmsg.append(subsection)
        
        if subsection.content.lower() in subsections:
            if subsection.content.lower() == "char sheets":
                del subsection.content
                
                dialog2 = await ctx.send("Options to use include are: `save` to update an entry of a session, `load` a previously saved session, or `new` to create a new entry. Type `cancel` to exit. In the case yhou need to delete a previously made entry, use `delete`.")
                killmsg.append(dialog2)
                
                mode = await self.client.wait_for("message", check = self.response(ctx))
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
                        
                        reqsessionid = await self.client.wait_for("message", check = self.response(ctx))
                        replyignore.append(reqsessionid)
                        killmsg.append(reqsessionid)
                        
                        dialog4 = await ctx.send("Is this your session?")
                        killmsg.append(dialog4)
                        
                        confirmation = await ctx.author.send(sessions[reqsessionid.content])
                        killmsg.append(confirmation)
                        
                        if confirmation.content.lower() in ["yes", "y"]:
                            dialog5 = await ctx.send("What character would you like to modify?")
                            killmsg.append(dialog5)
                            
                            modify = await self.client.wait_for("message", check = self.response(ctx))
                            replyignore.append(modify)
                            killmsg.append(modify)
                            
                            if int(modify.content) <= int(sessions[reqsessionid]["Number of Players: "]):
                                dialog6 = await ctx.send(f"Enter the player{modify.content}\'s character: ")
                                killmsg.append(dialog6)
                                
                                entry = await self.client.wait_for("message", check = self.response(ctx))
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
                        
                        plnum = await self.client.wait_for("message", check = self.response(ctx)) # Number of players
                        replyignore(plnum)
                        killmsg.append(plnum)
                        
                        pldes = [] # Description of players
                        
                        # Ask for description of each player then append to pldes
                        for player in range(int(plnum.content)):
                            dialog = await ctx.send(f"Enter the player{player + 1}\'s character: ")
                            killmsg.append(dialog)
                            
                            entry = await self.client.wait_for("message", check = self.response(ctx))
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
                        
                        id = await self.client.wait_for("message", check = self.response(ctx))
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
                        
                        session = await self.client.wait_for("message", check = self.response(ctx))
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
                            
                            confirm = await self.client.wait_for("message", check = self.response(ctx))
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