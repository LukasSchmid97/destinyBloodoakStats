from datetime import datetime

import discord

from functions.database import hasFlawless, getClearCount
from functions.dataTransformation import hasLowman
from functions.dataTransformation import hasCollectible, hasTriumph
from functions.formating import embed_message
from functions.network import getJSONfromURL
from static.dict import requirementHashes, getNameFromHashRecords, getNameFromHashCollectible
# check if user has permission to use this command
from static.globals import admin_role_id, dev_role_id, mod_role_id, role_ban_id


async def hasAdminOrDevPermissions(message, send_message=True):
    admin = discord.utils.get(message.guild.roles, id=admin_role_id)
    dev = discord.utils.get(message.guild.roles, id=dev_role_id)
    mod = discord.utils.get(message.guild.roles, id=mod_role_id)

    # also checking for Kigstns id, to make that shit work on my local version of the bot
    if message.author.id == 238388130581839872:
        return True

    if admin not in message.author.roles and dev not in message.author.roles and mod not in message.author.roles:
        if send_message:
            await message.channel.send(embed=embed_message(
                'Error',
                'You are not allowed to do that'
            ))
        return False
    return True


async def hasRole(playerid, role, year, br = True):
    """ br may be set to True if only True/False is exptected, set to False to get complete data on why or why not the user earned the role """
    data = {}

    roledata = requirementHashes[year][role]
    if not 'requirements' in roledata:
        print('malformatted requirementHashes')
        return [False, data]
    worthy = True

    for req in roledata['requirements']:
        if req == 'clears':
            creq = roledata['clears']
            i = 1
            for raid in creq:
                actualclears = getClearCount(playerid, raid['actHashes'])
                if not actualclears>= raid['count']:
                    #print(f'{playerid} is only has {actualclears} out of {raid["count"]} for {",".join([str(x) for x in raid["actHashes"]])}')
                    worthy = False

                data["Clears #" + str(i)] = str(actualclears) + " / " + str(raid['count'])
                i += 1

        elif req == 'flawless':
            has_fla = hasFlawless(playerid, roledata['flawless'])
            worthy &= has_fla

            data["Flawless"] = str(has_fla)

        elif req == 'collectibles':
            for collectible in roledata['collectibles']:
                has_col = await hasCollectible(playerid, collectible)
                worthy &= has_col

                if (not worthy) and br:
                    break
                
                if not br:
                    # get name of collectible
                    name = "No name here"
                    #str conversion required because dictionary is indexed on strings, not postiions
                    if str(collectible) in getNameFromHashCollectible.keys():
                        name = getNameFromHashCollectible[str(collectible)]
                    data[name] = str(has_col)

        elif req == 'records':
            for recordHash in roledata['records']:
                has_tri = await hasTriumph(playerid, recordHash)
                worthy &= has_tri

                if (not worthy) and br:
                    break
                
                if not br:
                    # get name of triumph
                    name = "No name here"
                    if str(recordHash) in getNameFromHashRecords.keys():
                        name = getNameFromHashRecords[str(recordHash)]
                    data[name] = str(has_tri)

        elif req == 'lowman':
            denies = sum([1 if 'denyTime' in key else 0 for key in roledata.keys()])
            timeParse = lambda i, spec: datetime.strptime(roledata[f'denyTime{i}'][spec], "%d/%m/%Y %H:%M")
            disallowed = [(timeParse(i, 'startTime'), timeParse(i, 'endTime')) for i in range(denies)]
            has_low = hasLowman(playerid,
                            roledata['playercount'], 
                            roledata['activityHashes'], 
                            flawless=roledata.get('flawless', False), 
                            disallowed=disallowed
                            )
            worthy &= has_low

            data["Lowman (" + str(roledata['playercount']) + " Players)"] = str(has_low)

        elif req == 'roles':
            for required_role in roledata['roles']:
                req_worthy, req_data = await hasRole(playerid, required_role, year, br = br)
                worthy &= req_worthy #only worthy if worthy for all required roles
                data = {**req_data, **data} #merging dicts, data dominates
                data[f'Role: {required_role}'] = req_worthy

        if (not worthy) and br:
            break

    return [worthy, data]

async def returnIfHasRoles(playerid, role, year):
    if (await hasRole(playerid, role, year))[0]:
        return role
    return None

async def getPlayerRoles(playerid, existingRoles = []):
    if not playerid:
        print('got empty playerid')
        return ([],[])
    print(f'getting roles for {playerid}')
    roles = []
    redundantRoles = []

    for year, yeardata in requirementHashes.items():
        for role, roledata in yeardata.items():
            #do not recheck existing roles or roles that will be replaced by existing roles
            if role in existingRoles or ('replaced_by' in roledata.keys() and any([x in existingRoles for x in roledata['replaced_by']])):
                roles.append(role)
                continue

            roleOrNone = await returnIfHasRoles(playerid, role, year)
            if roleOrNone:
                roles.append(roleOrNone)

    #remove roles that are replaced by others
    for yeardata in requirementHashes.values():
        for roleName, roledata in yeardata.items():
            if roleName not in roles:
                redundantRoles.append(roleName)
            if 'replaced_by' in roledata.keys():
                for superior in roledata['replaced_by']:
                    if superior in roles:
                        if roleName in roles:
                            roles.remove(roleName)
                            redundantRoles.append(roleName)
    
    return (roles, redundantRoles)

async def assignRolesToUser(roleList, discordUser, guild, reason=None):
    #takes rolelist as string array, userSnowflake, guild object
    if not discordUser:
        return False
    
    role_banned = discord.utils.get(guild.roles, name='Role Banned') or discord.utils.get(guild.roles, id=role_ban_id)
    if role_banned in discordUser.roles:
        return False

    for role in roleList:
        #print(guild.roles)
        roleObj = discord.utils.get(guild.roles, name=role) or discord.utils.get(guild.roles, id=role)
        if not roleObj:
            if guild.id in [669293365900214293]: #We only care about the descend discord
                print(f'assignable role doesn\'t exist in {guild.name} with id {guild.id}: {role}')
            continue
        if roleObj not in discordUser.roles:
            try:
                await discordUser.add_roles(roleObj, reason=reason)
                print(f'added role {roleObj.name} to user {discordUser.name} in server {guild.name}')
            except discord.errors.Forbidden:
                print(f'failed to add {roleObj.name} to user {discordUser.name} in server {guild.name}')
                return False
    return True

async def removeRolesFromUser(roleStringList, discordUser, guild, reason=None):
    removeRolesObjs = []
    for role in roleStringList:
        roleObj = discord.utils.get(guild.roles, name=role) or discord.utils.get(guild.roles, id=role)
        if roleObj is None and guild.id not in [556418279015448596, 724676552175910934]:
            print(f'removeable role doesn\'t exist: {role}')
            continue
        removeRolesObjs.append(roleObj)
    for roleObj in removeRolesObjs:
        #print(f'removed {roleObj.name} from {discordUser.name}')
        if roleObj in discordUser.roles:
            print(f'removed role {roleObj.name} from user {discordUser.name}')
            try:
                await discordUser.remove_roles(roleObj, reason=reason)
            except discord.errors.Forbidden:
                return False
    return True