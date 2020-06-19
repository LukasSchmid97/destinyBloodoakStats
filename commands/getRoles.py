from commands.base_command  import BaseCommand

from static.dict                    import requirementHashes, clanids
from functions.database             import lookupDestinyID, lookupDiscordID, getLastRaid, getFlawlessList
from functions.dataLoading          import updateDB, initDB, getNameToHashMapByClanid
from functions.dataTransformation   import getFullMemberMap, getUserIDbySnowflakeAndClanLookup
from functions.roles                import assignRolesToUser, removeRolesFromUser, getPlayerRoles
from functions.formating import     embed_message


import discord

from discord.ext import commands

raiderText = '⁣           Raider       ⁣'
achText = '⁣        Achievements       ⁣'

class getRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "Assigns you all the roles you've earned"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        if params:
            await message.channel.send(embed=embed_message(
                'Error',
                f'You can\'t do this for other users\n Use !setroles {params[0]} instead'
            ))
            return
        destinyID = lookupDestinyID(message.author.id)

        if not destinyID:
            fullMemberMap = getFullMemberMap()
            if not fullMemberMap:
                await message.channel.send(embed=embed_message(
                    'Error',
                    'Seems like bungo is offline, try again later'
                ))
                return
            destinyID = getUserIDbySnowflakeAndClanLookup(message.author, fullMemberMap)
            if not destinyID:
                await message.channel.send(embed=embed_message(
                    'Error',
                    'Didn\'t find your destiny profile, sorry'
                ))
                return

        updateDB(destinyID)
        
        async with message.channel.typing():
            (roleList,removeRoles) = getPlayerRoles(destinyID, [role.name for role in message.author.roles])
            
            await assignRolesToUser(roleList, message.author, message.guild)
            await removeRolesFromUser(removeRoles,message.author,message.guild)

            for role in roleList:
                if role in requirementHashes['Addition']:
                    await message.author.add_roles(discord.utils.get(message.guild.roles, name=achText))
                else:
                    await message.author.add_roles(discord.utils.get(message.guild.roles, name=raiderText))
            rolesgiven = ', '.join(roleList)
            if len(rolesgiven) == 0:
                await message.channel.send(embed=embed_message(
                    'Error',
                    f'You don\'t seem to have any roles.\nIf you believe this is an Error, refer to one of the <@&670397357120159776>\nOtherwise check <#686568386590802000> to see what you could acquire'
                ))
                return
            await message.channel.send(embed=embed_message(
                f'{message.author.name} Roles',
                f'Added the roles {rolesgiven}'
            ))

class lastRaid(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "gets your last raid"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received

    async def handle(self, params, message, client):
        ctx = await client.get_context(message)
        user = message.author
        if params:
            user = await commands.MemberConverter().convert(ctx, params[0])

        destinyID = lookupDestinyID(user.id)
        updateDB(destinyID)
        await message.channel.send(getLastRaid(destinyID))

class flawlesses(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "flaweless hashes"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received

    async def handle(self, params, message, client):
        ctx = await client.get_context(message)
        user = message.author
        if params:
            user = await commands.MemberConverter().convert(ctx, params[0])
        async with message.channel.typing():
            destinyID = lookupDestinyID(user.id)
            updateDB(destinyID)
            await message.channel.send(getFlawlessList(destinyID))

class setRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[admin] Assigns the mentioned user his/her earned roles"
        params = ['user']
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received

    async def handle(self, params, message, client):
        ctx = await client.get_context(message)
        user = await commands.MemberConverter().convert(ctx, params[0])
        destinyID = lookupDestinyID(user.id)
        if not destinyID:
            fullMemberMap = getFullMemberMap()
            if not fullMemberMap:
                await message.channel.send(embed=embed_message(
                    'Error',
                    'Seems like bungo is offline, try again later'
                ))
                return
            destinyID = getUserIDbySnowflakeAndClanLookup(user, fullMemberMap)
            if not destinyID:
                await message.channel.send(embed=embed_message(
                    'Error',
                    'Didn\'t find the destiny profile, sorry'
                ))
                return
        status_msg = await message.channel.send(embed=embed_message(
            'Working...',
            'Updating DB and assigning roles...'
        ))
        status_msg = await message.channel.fetch_message(status_msg.id)
        updateDB(destinyID)
        
        async with message.channel.typing():
            (roleList,removeRoles) = getPlayerRoles(destinyID, [role.name for role in user.roles])
            
            await assignRolesToUser(roleList, user, message.guild)
            await removeRolesFromUser(removeRoles,user,message.guild)

            for role in roleList:
                if role in requirementHashes['Addition']:
                    await user.add_roles(discord.utils.get(message.guild.roles, name=achText))
                else:
                    await user.add_roles(discord.utils.get(message.guild.roles, name=raiderText))
            rolesgiven = ', '.join(roleList)
            if len(rolesgiven) == 0:
                await status_msg.edit(embed=embed_message(
                    'Error',
                    f'You don\'t seem to have any roles.\nIf you believe this is an Error, refer to one of the @Developers\nOtherwise check <#686568386590802000> to see what you could acquire'
                ))
                return
            await status_msg.edit(embed=embed_message(
                f'{user.name} Roles',
                f'Added the roles {rolesgiven}'
            ))

#improvable TODO
class removeAllRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] removes a certain users roles"
        params = ['User']
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        admin = discord.utils.get(message.guild.roles, name='Admin')
        dev = discord.utils.get(message.guild.roles, name='Developer') 
        discordID = params[0]
        if admin not in message.author.roles and dev not in message.author.roles and not message.author.id == params[0]:
            await message.channel.send(embed=embed_message(
                'Error',
                'You are not allowed to do that'
            ))
            return
        roles = []
        for yeardata in requirementHashes.values():		
            for role in yeardata.keys():
                roles.append(role)
        await removeRolesFromUser(roles, client.get_user(int(discordID)), message.guild)

class checkNames(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] check name mappings"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        for discordUser in message.guild.members:
            destinyID = None
            destinyID = lookupDestinyID(discordUser.id)
            if destinyID:
                await message.channel.send(f'{discordUser.name} ({discordUser.nick}): https://raid.report/pc/{destinyID}')
                continue
            destinyID = getUserIDbySnowflakeAndClanLookup(discordUser,getFullMemberMap())
            await message.channel.send(f'{discordUser.name} ({discordUser.nick}): https://raid.report/pc/{destinyID}')

class checkNewbies(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] check people"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        naughtylist = []
        for clanid,name in clanids.items():
            await message.channel.send(f'checking clan {name}')
            clanmap = getNameToHashMapByClanid(clanid)
            for username, userid in clanmap.items():
                discordID = lookupDiscordID(userid)
                if discordID:
                    user = client.get_user(discordID)
                    if not user:
                        await message.channel.send(f'[ERROR] {username} with destinyID {userid} has discordID {discordID} but it is faulty')
                        continue
                    #await message.channel.send(f'{username} is in Discord with name {user.name}')
                else:
                    naughtylist.append(username)
                    await message.channel.send(f'{username} with ID {userid} is not in Discord (or not recognized by the bot)')
        await message.channel.send(f'users to check: {", ".join(naughtylist)}')


class listDescend(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] list all discordusers that are in the 'The Descent' clan"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        descendid = 4107840
        nameidmap = getNameToHashMapByClanid(descendid)
        nameidarr = [(name,id_) for (name,id_) in nameidmap.items()]
        namearr = [name for (name, _) in nameidarr]
        idarr = [int(id_) for (_, id_) in nameidarr]
        negativelist = [id_ for id_ in idarr]
        #await message.channel.send(f'All of Descend:{zip(namearr,idarr)}')
        async with message.channel.typing():
            await message.channel.send(f'**Members of Descend in this discord:**')
            for discordUser in message.guild.members:

                destinyID = lookupDestinyID(discordUser.id)
                if not destinyID:
                    destinyID = int(getUserIDbySnowflakeAndClanLookup(discordUser,nameidmap))
                if not destinyID:
                    continue

                if destinyID in idarr:
                    negativelist.remove(destinyID)
                    name = None
                    for (user, userid) in zip(namearr,idarr):
                        if userid == destinyID:
                            name = user
                    await message.channel.send(f'{discordUser.name} ({discordUser.nick}) as {name}')

            await message.channel.send(f'**Members of Descend __not__ in this discord:**')
            for dID in negativelist:
                for (user, userid) in zip(namearr,idarr):
                    if dID == userid:
                        await message.channel.send(f'{user} : {userid}')


class assignAllRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] Assigns everyone the roles they earned"
        params = []
        super().__init__(description, params)
    
    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        admin = discord.utils.get(message.guild.roles, name='Admin')
        dev = discord.utils.get(message.guild.roles, name='Developer') 
        if admin not in message.author.roles and dev not in message.author.roles:
            await message.channel.send('You are not allowed to do that')
            return
        await message.channel.send('Updating DB...')
        initDB()
        await message.channel.send('Assigning roles...')
        for discordUser in message.guild.members:
            destinyID = lookupDestinyID(discordUser.id)
            if not destinyID:
                destinyID = getUserIDbySnowflakeAndClanLookup(discordUser,getFullMemberMap())
                if not destinyID:
                    await message.channel.send(f'No destinyID found for {discordUser.name}')
                    continue

            async with message.channel.typing():
                (newRoles, removeRoles) = getPlayerRoles(destinyID, [role.name for role in discordUser.roles])
                await assignRolesToUser(newRoles, discordUser, message.guild)
                await removeRolesFromUser(removeRoles, discordUser, message.guild)

                roletext = ', '.join(newRoles)
                await message.channel.send(f'Assigned roles {roletext} to {discordUser.name}')

        await message.channel.send('All roles assigned')
