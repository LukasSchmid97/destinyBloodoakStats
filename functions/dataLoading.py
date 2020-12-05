import asyncio
import json
import os
import sqlite3
import zipfile
from datetime import timedelta, datetime

import aiohttp
import pandas

from functions.database import db_connect, insertActivity, insertCharacter, insertInstanceDetails, updatedPlayer, \
    lookupDiscordID, lookupSystem
from functions.database import getSystemAndChars, getLastUpdated, instanceExists
from functions.network import getJSONfromURL, getComponentInfoAsJSON, getJSONwithToken
from static.config import CLANID


async def getJSONfromRR(playerID):
    """ Gets a Players stats from the RR-API """
    requestURL = 'https://b9bv2wd97h.execute-api.us-west-2.amazonaws.com/prod/api/player/{}'.format(playerID)
    return await getJSONfromURL(requestURL)

async def getTriumphsJSON(playerID):
    """ returns the json containing all triumphs the player <playerID> has """
    achJSON = await getComponentInfoAsJSON(playerID, 900)
    if not achJSON:
        return None
    if 'data' not in achJSON['Response']['profileRecords']:
        return None
    return achJSON['Response']['profileRecords']['data']['records']

async def getCharacterList(destinyID):
    ''' returns a (system, [characterids]) tuple '''
    charURL = "https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/?components=100,200"
    membershipType = lookupSystem(destinyID)
    characterinfo = await getJSONfromURL(charURL.format(membershipType, destinyID))
    if characterinfo:
        return (membershipType, list(characterinfo['Response']['characters']['data'].keys()))
    print(f'no account found for destinyID {destinyID}')
    return (None,[])

racemap = {
    2803282938: 'Awoken',
    898834093: 'Exo',
    3887404748: 'Human'
} 
gendermap = {
    2204441813: 'Female',
    3111576190: 'Male',
}
classmap = {
    671679327: 'Hunter',
    2271682572: 'Warlock',
    3655393761: 'Titan'
}

async def OUTDATEDgetSystem(destinyID):
    ''' returns system '''
    charURL = "https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/?components=100,200"
    platform = None
    for i in [3, 2, 1, 4, 5, 10, 254]:
        characterinfo = await getJSONfromURL(charURL.format(i, destinyID))
        if characterinfo:
            platform = characterinfo["Response"]["profile"]["data"]["userInfo"]["membershipType"]
            break
    return platform

# OUTDATED. Use membershipType = lookupSystem(destinyID)
async def getCharactertypeList(destinyID):
    ''' returns a [charID, type] tuple '''
    charURL = "https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/?components=100,200"
    membershipType = lookupSystem(destinyID)
    characterinfo = await getJSONfromURL(charURL.format(membershipType, destinyID))
    if characterinfo:
        return [(char["characterId"], f"{racemap[char['raceHash']]} {gendermap[char['genderHash']]} {classmap[char['classHash']]}") for char in characterinfo['Response']['characters']['data'].values()]
    print(f'no account found for destinyID {destinyID}')
    return (None,[])

async def getPlayersPastPVE(destinyID, mode : int = 7, earliest_allowed_time : datetime = None, latest_allowed_time : datetime = None):
    """
    Generator which returns all activities whith an extra field < activity['charid'] = characterID >
    For more Info visit https://bungie-net.github.io/multi/schema_Destiny-HistoricalStats-DestinyHistoricalStatsPeriodGroup.html#schema_Destiny-HistoricalStats-DestinyHistoricalStatsPeriodGroup

    :mode - Describes the mode, see https://bungie-net.github.io/multi/schema_Destiny-HistoricalStats-Definitions-DestinyActivityModeType.html#schema_Destiny-HistoricalStats-Definitions-DestinyActivityModeType
        Everything	0
        Story	    2
        Strike	    3
        Raid	    4
        AllPvP	    5
        Patrol	    6
        AllPvE	    7
        ...
    :earliest_allowed_time - takes datetime.datetime and describes the lower cutoff
    :latest_allowed_time - takes datetime.datetime and describes the higher cutoff
    """

    platform, charIDs = await getCharacterList(destinyID)

    # if player has no characters for some reason
    if not charIDs:
        return

    for characterID in charIDs:
        br = False
        page = -1
        while True:
            page += 1
            staturl = f"https://www.bungie.net/Platform/Destiny2/{platform}/Account/{destinyID}/Character/{characterID}/Stats/Activities/?mode={mode}&count=250&page={page}"

            # break once threshold is reached
            if br:
                break

            # get activities
            rep = await getJSONfromURL(staturl)

            # break if empty, fe. when pages are over
            if not rep or not rep['Response']:
                break

            # loop through all activities
            for activity in rep['Response']['activities']:
                # check times if wanted
                if earliest_allowed_time or latest_allowed_time:
                    activity_time = datetime.strptime(activity["period"], "%Y-%m-%dT%H:%M:%SZ")

                    # check if the activity started later than the earliest allowed, else break and continue with next char
                    # This works bc Bungie sorts the api with the newest entry on top
                    if earliest_allowed_time:
                        if activity_time < earliest_allowed_time:
                            br = True
                            break

                    # check if the time is still in the timeframe, else pass this one and do the next
                    if latest_allowed_time:
                        if activity_time > latest_allowed_time:
                            pass

                # add character info to the activity
                activity['charid'] = characterID

                yield activity


# https://bungie-net.github.io/multi/schema_Destiny-DestinyComponentType.html#schema_Destiny-DestinyComponentType
async def getProfile(destinyID, *components, with_token=False):
    url = 'https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/?components={}'
    membershipType = lookupSystem(destinyID)
    if with_token:
        statsResponse = await getJSONwithToken(url.format(membershipType, destinyID, ','.join(map(str, components))), lookupDiscordID(destinyID))
        if statsResponse["result"]:
            return statsResponse["result"]['Response']

    else:
        statsResponse = await getJSONfromURL(url.format(membershipType, destinyID, ','.join(map(str, components))))
        if statsResponse:
            return statsResponse['Response']
    return None


async def getStats(destinyID):
    url = 'https://stats.bungie.net/Platform/Destiny2/{}/Account/{}/Stats/'
    membershipType = lookupSystem(destinyID)
    statsResponse = await getJSONfromURL(url.format(membershipType, destinyID))
    if statsResponse:
        return statsResponse['Response']
    return None


async def getAggregateStatsForChar(destinyID, system, characterID):
    url = 'https://stats.bungie.net/Platform/Destiny2/{}/Account/{}/Character/{}/Stats/AggregateActivityStats/'
    statsResponse = await getJSONfromURL(url.format(system, destinyID, characterID))
    if statsResponse:
        return statsResponse['Response']
    return None


# returns the item data - https://bungie-net.github.io/#/components/schemas/Destiny.Entities.Items.DestinyItemComponent
async def getItemDefinition(destinyID, system, itemID, components):
    url = 'https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/Item/{}/?components={}'
    statsResponse = await getJSONfromURL(url.format(system, destinyID, itemID, components))
    if statsResponse:
        return statsResponse['Response']
    return None


# returns all items in bucket. Deafult is vault hash, for others search "bucket" at https://data.destinysets.com/
async def getInventoryBucket(destinyID, bucket=138197802):
    items = (await getProfile(destinyID, 102, with_token=True))["profileInventory"]["data"]["items"]
    ret = []
    print(items)
    for item in items:
        if item["bucketHash"] == bucket:    # vault hash
            ret.append(item)

    return ret


# gets the current artifact, which includes the level
async def getArtifact(destinyID):
    return (await getProfile(destinyID, 104, with_token=True))['profileProgression']['data']['seasonalArtifact']


# returns all items in inventory
async def getCharacterGear(destinyID):
    items = []
    chars = await getCharacterList(destinyID)

    # not equiped on chars
    char_inventory = (await getProfile(destinyID, 201, with_token=True))["characterInventories"]["data"]
    for char in chars[1]:
        items.extend(char_inventory[char]["items"])

    # equiped on chars
    char_inventory = (await getProfile(destinyID, 205))['characterEquipment']["data"]
    for char in chars[1]:
        items.extend(char_inventory[char]["items"])

    return items

async def getCharacterGearAndPower(destinyID):
    items = []
    chars = await getCharacterList(destinyID)

    # not equiped on chars
    playerProfile = (await getProfile(destinyID, 201, 205, 300, with_token=True))
    itempower = {weaponid:int(weapondata.get("primaryStat", {"value":0})['value']) for weaponid, weapondata in playerProfile["itemComponents"]["instances"]["data"].items()}
    itempower['none'] = 0
    for char in chars[1]:
        charitems = playerProfile["characterInventories"]["data"][char]["items"] + playerProfile['characterEquipment']["data"][char]["items"]
        charpoweritems = map(lambda charitem:dict(charitem, **{'lightlevel':itempower[charitem.get('itemInstanceId', 'none')]}), charitems)
        items.extend(charpoweritems)

    return items

# returns all items in vault + inventory. Also gets ships and stuff - not only armor / weapons
async def getAllGear(destinyID):
    # vault
    items = await getInventoryBucket(destinyID)

    items.extend(await getCharacterGear(destinyID))

    # returns a list with the dicts of the items
    return items


# returns list of all copies of that piece
async def getGearPiece(destinyID, itemID):
    items = await getAllGear(destinyID)

    instances = []
    for item in items:
        if item["itemHash"] == itemID:
            instances.append(item)

    return instances


# returns the amount of kills done with all copies of that weapon in vault / inventory
async def getWeaponKills(destinyID, itemID):
    async def getItemData(destinyID, system, uniqueItemID):
        try:
            ret = (await getItemDefinition(destinyID, system, uniqueItemID, 309))["plugObjectives"]["data"][
                "objectivesPerPlug"]
            ret = ret[next(iter(ret))][0]
            return ret["progress"]
        except KeyError:
            return 0

    kills = 0

    instances = await getGearPiece(destinyID, itemID)
    if not instances:
        return kills

    system = (await getCharacterList(destinyID))[0]

    for item in instances:
        kills += await getItemData(destinyID, system, item["itemInstanceId"])

    return kills



# async def getStatsForChar(destinyID, characterID):
#     url = 'https://stats.bungie.net/Platform/Destiny2/{}/Account/{}/Stats/'
#     for system in [3,2,1,4,5,10,254]:
#         statsResponse = await getJSONfromURL(url.format(system, destinyID))
#         if statsResponse:
#             for char in statsResponse['Response']['characters']:
#                 if char['characterId'] == characterID:
#                     return char['merged']['allTime']
#     return None

async def getNameToHashMapByClanid(clanid):
    requestURL = "https://www.bungie.net/Platform/GroupV2/{}/members/".format(clanid) #memberlist
    memberJSON = await getJSONfromURL(requestURL)
    if not memberJSON:
        return {} 
    memberlist = memberJSON['Response']['results']
    memberids  = dict()
    for member in memberlist:
        memberids[member['destinyUserInfo']['LastSeenDisplayName']] = member['destinyUserInfo']['membershipId']
    return memberids

async def getNameAndCrossaveNameToHashMapByClanid(clanid):
    requestURL = "https://www.bungie.net/Platform/GroupV2/{}/members/".format(clanid) #memberlist
    memberJSON = await getJSONfromURL(requestURL)
    if not memberJSON:
        return {}
    memberlist = memberJSON['Response']['results']
    memberids  = dict()
    for member in memberlist:
        if 'bungieNetUserInfo' in member.keys():
            memberids[member['destinyUserInfo']['membershipId']] = (member['destinyUserInfo']['LastSeenDisplayName'], member['bungieNetUserInfo']['displayName'])
        else:
            memberids[member['destinyUserInfo']['membershipId']] = (member['destinyUserInfo']['LastSeenDisplayName'], 'none')
    return memberids


async def getPGCR(instanceID):
    pgcrurl = f'https://www.bungie.net/Platform/Destiny2/Stats/PostGameCarnageReport/{instanceID}/'
    return await getJSONfromURL(pgcrurl)


# type = "DestinyInventoryItemDefinition" (fe.), hash = 3993415705 (fe)   - returns MT
async def returnManifestInfo(type, hash):
    info = await getJSONfromURL(f'http://www.bungie.net/Platform/Destiny2/Manifest/{type}/{hash}/')

    if info:
        return info
    else:
        return None

# returns the hash of the item if found
async def searchArmory(type, searchTerm):
    info = await getJSONfromURL(f'http://www.bungie.net/Platform/Destiny2/Armory/Search/{type}/{searchTerm}/')

    try:
        return info["Response"]["results"]["results"][0]["hash"]
    except:
        return None


async def getManifest():
    manifest_url = 'http://www.bungie.net/Platform/Destiny2/Manifest/'
    binaryLocation = "cache/MANZIP"
    os.makedirs(os.path.dirname(binaryLocation), exist_ok=True)

    #get the manifest location from the json
    async with aiohttp.ClientSession() as session:
        async with session.get(url=manifest_url) as r:
            manifest = await r.json()
    mani_url = 'http://www.bungie.net' + manifest['Response']['mobileWorldContentPaths']['en']

    #Download the file, write it to 'MANZIP'
    async with aiohttp.ClientSession() as session:
        async with session.get(url=mani_url) as r:
            with open(binaryLocation, "wb") as zip:
                zip.write(r.content)

    #Extract the file contents, and rename the extracted file to 'Manifest.content'
    with zipfile.ZipFile(binaryLocation) as zip:
        name = zip.namelist()
        zip.extractall()
    os.rename(name[0], 'cache/Manifest.content')

async def fillDictFromDB(dictRef, table):
    if not os.path.exists('cache/' + table + '.json'): 
        if not os.path.exists('cache/Manifest.content'):
            await getManifest()

        #Connect to DB
        con = sqlite3.connect('cache/Manifest.content')
        cur = con.cursor()

        #Query the DB
        cur.execute(
        '''SELECT 
            json
        FROM 
        ''' + table
        )
        items = cur.fetchall()
        item_jsons = [json.loads(item[0]) for item in items]
        con.close()

        #Iterate over DB-JSONs and put named ones into the corresponding dictionary
        for ijson in item_jsons:
            if 'name' in ijson['displayProperties'].keys():
                dictRef[ijson['hash']] = ijson['displayProperties']['name']
        with open('cache/' + table + '.json', 'w') as outfile:
            json.dump(dictRef, outfile)
    else:
        with open('cache/' + table + '.json') as json_file:
            dictRef.update(json.load(json_file))


async def insertIntoDB(destinyID, pve):
    if not destinyID:
        return None
    #print('inserting into db...')
    period = datetime.strptime(pve['period'], "%Y-%m-%dT%H:%M:%SZ")
    activityHash = pve['activityDetails']['directorActivityHash']
    #print(activityHash)
    instanceID = pve['activityDetails']['instanceId']
    if instanceExists(instanceID):
        #print('cancelling insertion')
        return False
    activityDurationSeconds = int(pve['values']['activityDurationSeconds']['basic']['value'])
    completed = int(pve['values']['completed']['basic']['value'])
    mode = int(pve['activityDetails']['mode'])
    if completed and not int(pve['values']['completionReason']['basic']['value']):
        if not (pgcr := await getPGCR(instanceID)):
            return
        pgcrdata = pgcr['Response']

        startingPhaseIndex = pgcrdata['startingPhaseIndex']
        deaths = 0
        players = set()
        for player in pgcrdata['entries']:
            lightlevel = player['player']['lightLevel']
            playerID = player['player']['destinyUserInfo']['membershipId']
            players.add(playerID)
            characterID = player['characterId']
            playerdeaths = int(player['values']['deaths']['basic']['displayValue'])
            deaths += playerdeaths
            displayname = None
            if 'displayName' in player['player']['destinyUserInfo']:
                displayname = player['player']['destinyUserInfo']['displayName']
            completed = int(player['values']['completed']['basic']['value'])
            opponentsDefeated = player['values']['opponentsDefeated']['basic']['value']
            system = player['player']['destinyUserInfo']['membershipType']
            insertCharacter(playerID, characterID, system)
            insertInstanceDetails(instanceID, playerID, characterID, lightlevel, displayname, deaths, opponentsDefeated, completed)
        playercount = len(players)
        #print(f'inserting {instanceID}')
        insertActivity(instanceID, activityHash, activityDurationSeconds, period, startingPhaseIndex, deaths, playercount, mode)
    return True
        
async def updateDB(destinyID):
    if not destinyID:
        return

    charcount = len((await getCharacterList(destinyID))[1])
    if charcount == 0:
        print(f'no characters found for {destinyID}')
        return
    #print(await getCharacterList(destinyID)[1])
    processes = []
    lastUpdate = getLastUpdated(destinyID)
    donechars = []
    print(f'checking {charcount} characters')

    falses, results = 0, 0
    async for pve in getPlayersPastPVE(destinyID):
        if 'period' not in pve.keys():
            print('period not in pve')

        if len(donechars) == charcount:
            print(f'stopped loading {destinyID} at ' + period.strftime("%d %m %Y"))
            updatedPlayer(destinyID)
            break

        if pve['charid'] in donechars:
            #print('charid in donechars... skipping...')
            continue
        #print(pve)
        period = datetime.strptime(pve['period'], "%Y-%m-%dT%H:%M:%SZ")

        if period < (lastUpdate - timedelta(days=2)):
            print(f'char {pve["charid"]} caught up to {pve["period"]}')
            donechars.append(pve['charid'])
            continue

        result = await insertIntoDB(destinyID, pve)
        if not result:
            # print('returing false')
            falses += 1
        else:
            results += 1

    updatedPlayer(destinyID)
    print(f'done updating {destinyID} with {falses} errors and {results} new entries')


async def initDB():
    con = db_connect()
    cur = con.cursor()
    playerlist = cur.execute('SELECT destinyID FROM discordGuardiansToken')
    playerlist = [p[0] for p in playerlist]
    for player in playerlist:
        await updateDB(player)
    print(f'done updating the db')


def getSeals(client):
    # if file doesn't exist, call the daily running event (useful for first usage)
    try:
        file = pandas.read_pickle('database/seals.pickle')
    except FileNotFoundError:
        from events.backgroundTasks import refreshSealPickle
        rf = refreshSealPickle()
        fut = asyncio.run_coroutine_threadsafe(rf.run(), client.loop)
        try:
            fut.result()
            print(fut)
            file = pandas.read_pickle('database/seals.pickle')
        except Exception as exc:
            print(f'generated an exception: {exc}')

    # returns list [[hash, name, displayName, hasExpiration], ...]
    return file["seals"][0]

async def getClanMembers(client):
    # get all clan members {destinyID: discordID}
    memberlist = {}
    for member in (await getJSONfromURL(f"https://www.bungie.net/Platform/GroupV2/{CLANID}/Members/"))["Response"][
        "results"]:
        destinyID = int(member["destinyUserInfo"]["membershipId"])
        discordID = lookupDiscordID(destinyID)
        if discordID is not None:
            memberlist.update({destinyID: discordID})

    return memberlist


#TODO replace with DB and version checks

