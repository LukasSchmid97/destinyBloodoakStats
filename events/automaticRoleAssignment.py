from events.base_event              import BaseEvent

from functions.roles                import assignRolesToUser, removeRolesFromUser, getPlayerRoles
from functions.database             import lookupDiscordID, lookupDestinyID, getToken
from functions.dataLoading          import initDB
from functions.network import getJSONfromURL
from static.config import CLANID, BOTDEVCHANNELID, DISCORDCLANROLEID

import discord

from itertools import compress

class AutomaticRoleAssignment(BaseEvent):
    """Will automatically update the roles"""

    def __init__(self):
        interval_minutes = 1440 # Set the interval for this event 1440 = 24h
        super().__init__(interval_minutes)
    
    async def run(self, client):
        print('running the automatic role assignment...')
        async def updateUser(discordUser):
            if discordUser.bot:
                return (None, None, None)

            destinyID = lookupDestinyID(discordUser.id)
            if not destinyID:
                return (None, None, None)
                #await newtonslab.send(f'Auto-Matched {discordUser.name} with {destinyID} \n check https://raid.report/pc/{destinyID}' )

            #gets the roles of the specific player and assigns/removes them
            (newRoles, removeRoles) = await getPlayerRoles(destinyID, [role.name for role in discordUser.roles]) #the list of roles may be used to not check existing roles
            

            return (discordUser, newRoles, removeRoles)
        
        #aquires the newtonslab channel from the descend server and notifies about starting
        newtonslab = client.get_channel(BOTDEVCHANNELID)
        #await newtonslab.send('running db update...')
        async with newtonslab.typing():
            await initDB()
        #await newtonslab.send('db done')
        #await newtonslab.send('running role update...')

        async with newtonslab.typing():
            #Since I'm too lazy to find out the guild-id, this is how I get the guild-object
            guild = newtonslab.guild

            news = []
            for member in guild.members:
                news.append(await updateUser(member))

            newstext = 'done with role update <:CaydeThumbsUp:670997683774685234>\n'

            for discordUser, newRoles, removeRoles in news:
                if not discordUser:
                    continue
                await assignRolesToUser(newRoles, discordUser, guild)
                await removeRolesFromUser(removeRoles, discordUser, guild)

                existingRoles = [er.name for er in discordUser.roles]
                addBools = [nr not in existingRoles for nr in newRoles]
                removeBools = [rr in existingRoles for rr in removeRoles]

                addrls = list(compress(newRoles, addBools))
                removerls = list(compress(removeRoles, removeBools))

                if addrls or removerls:
                    newstext += f'Updated player {discordUser.name} by adding {", ".join(addrls or ["nothing"])} and removing {", ".join(removerls or ["nothing"])}\n'

            await newtonslab.send(newstext)
        
        #await newtonslab.send('done with daily update <:CaydeThumbsUp:670997683774685234>')


class AutoRegisteredRole(BaseEvent):
    """Will automatically update the registration and the guest role"""
    def __init__(self):
        interval_minutes = 30  # Set the interval for this event 1440 = 24h
        super().__init__(interval_minutes)

    async def run(self, client):
        raiderText = '⁣           Raider       ⁣'
        raiderId = 670385313994113025
        achText = '⁣        Achievements       ⁣'
        achId = 670385837044662285
        miscText = '⁣           Misc       ⁣  ⁣  ⁣'
        miscId = 670395920327639085



        # get all clan members discordID
        memberlist = []
        for member in (await getJSONfromURL(f"https://www.bungie.net/Platform/GroupV2/{CLANID}/Members/"))["Response"]["results"]:
            destinyID = int(member["destinyUserInfo"]["membershipId"])
            discordID = lookupDiscordID(destinyID)
            if discordID is not None:
                memberlist.append(discordID)

        for guild in client.guilds:
            newtonsLab = discord.utils.get(guild.channels, id=BOTDEVCHANNELID)
            for member in guild.members:
                # dont do that for bots
                if not member.bot:
                    # add "Registered" if they have a token but not the role
                    if getToken(member.id):
                        if discord.utils.get(guild.roles, name="Not Registered") in member.roles:
                            await removeRolesFromUser(["Not Registered"], member, guild)
                            await assignRolesToUser(["Registered"], member, guild)
                    # add "Not Registered" if they have no token but the role (after unregister)
                    else:
                        if discord.utils.get(guild.roles, name="Registered") in member.roles:
                            await removeRolesFromUser(["Registered"], member, guild)
                            await assignRolesToUser(["Not Registered"], member, guild)

                    # add clan role if user is in clan and doesn't have clan role
                    if discord.utils.get(guild.roles, id=DISCORDCLANROLEID) not in member.roles:
                        if member.id in memberlist:
                            await assignRolesToUser([DISCORDCLANROLEID], member, guild)
                            if newtonsLab:
                                await newtonsLab.send(f"Added Descend role to {member.mention}")
                    # Also remove it if no longer in clan
                    elif discord.utils.get(guild.roles, id=DISCORDCLANROLEID) in member.roles:
                        if member.id not in memberlist:
                            await removeRolesFromUser([DISCORDCLANROLEID], member, guild)
                            if newtonsLab:
                                await newtonsLab.send(f"Removee Descend role from {member.mention}")

                    # add @guest if the clan role doesn't exist
                    if discord.utils.get(guild.roles, id=DISCORDCLANROLEID) not in member.roles:
                        await assignRolesToUser(["Guest"], member, guild)
                    # remove @guest if in clan
                    elif discord.utils.get(guild.roles, id=DISCORDCLANROLEID) in member.roles:
                        await removeRolesFromUser(["Guest"], member, guild)

                    # add filler roles to everyone
                    if discord.utils.get(guild.roles, id=raiderId) not in member.roles:
                        await assignRolesToUser([raiderId], member, guild)
                    if discord.utils.get(guild.roles, id=achId) not in member.roles:
                        await assignRolesToUser([achId], member, guild)
                    if discord.utils.get(guild.roles, id=miscId) not in member.roles:
                        await assignRolesToUser([miscId], member, guild)
