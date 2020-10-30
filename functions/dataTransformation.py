import pathlib
from datetime import datetime

import matplotlib

from functions.dataLoading import getStats, getTriumphsJSON, getPGCR, getPlayersPastPVE, getNameToHashMapByClanid
from functions.database import db_connect
from functions.network import getComponentInfoAsJSON
from static.dict import getNameFromHashInventoryItem, clanids

matplotlib.use('Agg')
import matplotlib.pyplot as plt

#https://data.destinysets.com/

async def hasCollectible(playerid, cHash):
    """ Returns boolean whether the player <playerid> has the collecible <cHash> """
    userCollectibles = await getComponentInfoAsJSON(playerid, 800)
    if not userCollectibles or 'data' not in userCollectibles['Response']['profileCollectibles']:
        return False
    collectibles = userCollectibles['Response']['profileCollectibles']['data']['collectibles']
    if str(cHash) not in collectibles:
        return False
    return collectibles[str(cHash)]['state'] & 1 == 0
#   Check whether it's not (not aquired), which means that the firstbit can't be 1   
#   https://bungie-net.github.io/multi/schema_Destiny-DestinyCollectibleState.html

def getClearCount(playerid, activityHashes):
    """ Gets the full-clearcount for player <playerid> of activity <activityHash> """
    con = db_connect()
    cur = con.cursor()
    sqlite_select = f"""SELECT COUNT(t1.instanceID)
                        FROM (  SELECT instanceID FROM activities
                                WHERE activityHash IN ({','.join(['?']*len(activityHashes))})
                                AND startingPhaseIndex <= 2) t1
                        JOIN (  SELECT DISTINCT(instanceID)
                                FROM instancePlayerPerformance
                                WHERE playerID = ?
                                ) ipp 
                        ON (ipp.instanceID = t1.instanceID)
                        """
    data_tuple = (*activityHashes, playerid)
    cur.execute(sqlite_select, data_tuple)
    (result,) = cur.fetchone()
    con.close()
    return result


def hasFlawless(playerid, activityHashes):
    """ returns the list of all flawless raids the player <playerid> has done """
    con = db_connect()
    cur = con.cursor()
    sqlite_select = f"""SELECT COUNT(t1.instanceID)
                        FROM (  SELECT instanceID FROM activities
                                WHERE activityHash IN ({','.join(['?']*len(activityHashes))})
                                AND startingPhaseIndex <= 2
                                AND deaths = 0) t1
                        JOIN (  SELECT DISTINCT(instanceID)
                                FROM instancePlayerPerformance
                                WHERE playerID = ?
                                ) ipp 
                        ON (ipp.instanceID = t1.instanceID)
                        """
    data_tuple = (*activityHashes, playerid)
    cur.execute(sqlite_select, data_tuple)
    (count,) = cur.fetchone()
    return count > 0

async def hasTriumph(playerid, recordHash):
    """ returns True if the player <playerid> has the triumph <recordHash> """
    status = True
    triumphs = await getTriumphsJSON(playerid)
    if triumphs is None:
        return False
    if str(recordHash) not in triumphs:
        return False
    for part in triumphs[str(recordHash)]['objectives']:
        status &= part['complete']
    return status

async def getPlayerCount(instanceID):
    pgcr = await getPGCR(instanceID)
    ingamechars = pgcr['Response']['entries']
    ingameids = set()
    for char in ingamechars:
        ingameids.add(char['player']['destinyUserInfo']['membershipId'])
    return len(ingameids)


def hasLowman(playerid, playercount, raidHashes, flawless=False, disallowed=[]):
    """ Default is flawless=False, disallowed is a list of (starttime, endtime) with datetime objects """
    con = db_connect()
    cur = con.cursor()
    #raidHashes = [str(r) for r in raidHashes]
    sqlite_select = f"""SELECT t1.instanceID, t1.deaths, t1.period
                        FROM (  SELECT instanceID, deaths, period FROM activities
                                WHERE activityHash IN ({','.join(['?']*len(raidHashes))})
                                AND playercount = ?) t1 
                        JOIN (  SELECT DISTINCT(instanceID)
                                FROM instancePlayerPerformance
                                WHERE playerID = ?
                                ) ipp
                        ON (ipp.instanceID = t1.instanceID)
                        """
    data_tuple = (*raidHashes,playercount, playerid)
    cur.execute(sqlite_select, data_tuple)
    verdict = False
    for (iid, deaths, period) in cur.fetchall():
        #print(f'{deaths} on {period} in {iid}')
        if not flawless or deaths == 0:
            verdict = True
            for starttime, endtime in disallowed:
                if starttime < period < endtime:
                    verdict = False
            if verdict:
                return True            
    con.close()
    return False

async def getIntStat(destinyID, statname):
    stats = await getStats(destinyID)
    if not stats:
        return -1
    stat = stats['mergedAllCharacters']['merged']['allTime'][statname]['basic']['value']
    return int(stat)

async def getCharStats(destinyID, characterID, statname):
    stats = await getStats(destinyID)
    for char in stats['characters']:
        if char['characterId'] == characterID:
            return char['merged']['allTime'][statname]['basic']['value']

async def getPossibleStats():
    stats = await getStats(4611686018468695677)
    for char in stats['characters']:
        return char['merged']['allTime'].keys()

async def isUserInClan(destinyID, clanid):
    isin = destinyID in await getNameToHashMapByClanid(clanid).values()
    print(f'{destinyID} is {isin} in {clanid}')
    return isin

fullMemberMap = {}
async def getFullMemberMap():
    if len(fullMemberMap) > 0:
        return fullMemberMap
    else:
        for clanid in clanids:
            fullMemberMap.update(await getNameToHashMapByClanid(clanid))
        return fullMemberMap

async def getGunsForPeriod(destinyID, pStart, pEnd):
    processes = []

    async for pve in getPlayersPastPVE(destinyID):
        if 'period' not in pve.keys():
            continue
        period = datetime.strptime(pve['period'], "%Y-%m-%dT%H:%M:%SZ")
        pS = datetime.strptime(pStart, "%Y-%m-%d")
        pE = datetime.strptime(pEnd, "%Y-%m-%d")

        if pS < period < pE:
            result = await getPGCR(pve['activityDetails']['instanceId'])
            if result['Response']:
                for entry in result['Response']['entries']:
                    if int(entry['player']['destinyUserInfo']['membershipId']) != int(destinyID):
                        # print(entry['player']['destinyUserInfo'])
                        continue
                    if not 'weapons' in entry['extended'].keys():
                        continue
                    # guns = entry['extended']['weapons']
                    # for gun in guns:
                    #     # gunids.append(gun['referenceId'])
                    #     if str(gun['referenceId']) not in gunkills:
                    #         gunkills[str(gun['referenceId'])] = 0
                    #     gunkills[str(gun['referenceId'])] += int(
                    #         gun['values']['uniqueWeaponKills']['basic']['displayValue'])

                # TODO

        if period < pS:
            break


async def getTop10PveGuns(destinyID):
    gunids = []
    gunkills = {}
    activities = getPlayersPastPVE(destinyID)
    instanceIds = [act['activityDetails']['instanceId'] for act in activities]
    pgcrlist = []

    processes = []
    for instanceId in instanceIds:
        result = await getPGCR(instanceId)
        if result:
            pgcrlist.append(result['Response'])

    for pgcr in pgcrlist:
        for entry in pgcr['entries']:
            if int(entry['player']['destinyUserInfo']['membershipId']) != int(destinyID):
               # print(entry['player']['destinyUserInfo'])
                continue
            if not 'weapons' in entry['extended'].keys():
                continue
            guns = entry['extended']['weapons']
            for gun in guns:
                #gunids.append(gun['referenceId'])
                if str(gun['referenceId']) not in gunkills:
                    gunkills[str(gun['referenceId'])] = 0
                gunkills[str(gun['referenceId'])] += int(gun['values']['uniqueWeaponKills']['basic']['displayValue'])

    #manifest = getManifestJson()

    #DestinyInventoryItemDefinitionLink = f"https://www.bungie.net{manifest['jsonWorldComponentContentPaths']['en']['DestinyInventoryItemDefinition']}"
    # DestinyInventoryItemDefinitionLink = "https://www.bungie.net/common/destiny2_content/json/en/DestinyInventoryItemDefinition-39a4e3a0-efbe-4356-beca-d87271a5c699.json"
    
    
    inventoryitemdefinition = getNameFromHashInventoryItem
    gunidlist = list(gunkills.keys())
    for gunid in gunidlist:
        gunname = inventoryitemdefinition[str(gunid)]['displayProperties']['name']
        gunkills[gunname] = int(gunkills[str(gunid)])
        del gunkills[str(gunid)]

    gunkillsorder = sorted(gunkills, reverse=True, key=lambda x : gunkills[x])    

    piedataraw = [gunkills[rankeditem] for rankeditem in gunkillsorder][:10]
    plt.pie(piedataraw, labels=gunkillsorder[:10])
    plt.savefig(f'{destinyID}.png')
    plt.clf()
    return pathlib.Path(__file__).parent / f'{destinyID}.png'