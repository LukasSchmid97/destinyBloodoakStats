import datetime
import json

import pandas

from events.base_event import BaseEvent
from functions.dataLoading import getTriumphsJSON, updateDB
from functions.database import getAllDestinyIDs, lookupDiscordID
from functions.network import getJSONfromURL


# todo delete
class refreshSealPickle(BaseEvent):
    def __init__(self):
        interval_minutes = 1340  # Set the interval for this event
        super().__init__(scheduler_type="interval", interval_minutes=interval_minutes)

    async def getTriumphData(self, triumph, not_available, cant_earn_anymore):
        rep = await getJSONfromURL(f"https://www.bungie.net/Platform/Destiny2/Manifest/DestinyRecordDefinition/{triumph}/")

        # converting to python dict (for true -> True conversion)
        rep = json.loads(json.dumps(rep))

        if rep and rep['Response']:
            try:
                if rep['Response']["titleInfo"]["hasTitle"]:
                    # ignore titles that don't have objectives
                    if rep['Response']["objectiveHashes"]:
                        if int(triumph) not in not_available:
                            still_available = bool(int(triumph) not in cant_earn_anymore)
                            return [
                                triumph,
                                rep['Response']["displayProperties"]["name"],
                                rep['Response']["titleInfo"]["titlesByGender"]["Male"],
                                still_available,
                            ]

            except Exception as exc:
                pass
                # print(f'generated an exception: {exc}')


    # Override the run() method
    # It will be called once every day
    async def run(self, *client):
        not_available = [
            837071607,  # shaxx
            1754815776,  # wishbringer
        ]
        cant_earn_anymore = [
            2254764897,  # MMIX
            2707428411,  # Undying
            2460356851,  # Dawn
            2945528800,  # flawless s10
            1983630873,  # Conqueror s10
            2860165064  # almighty
        ]

        print("Refreshing seals.pickle")

        # create dataframe if file doesn't exist
        try:
            file = pandas.read_pickle('database/seals.pickle')
        except FileNotFoundError:
            file = pandas.DataFrame({"date": [datetime.date.min]})

        triumphs = await getTriumphsJSON(4611686018467765462)

        seals = []
        if triumphs is None:
            return False

        # converting to python dict (for true -> True conversion)
        triumphs = json.loads(json.dumps(triumphs))

        for triumph in triumphs:
            result = await self.getTriumphData(triumph, not_available, cant_earn_anymore)
            if result:
                seals.append(result)

        # print(seals)

        # write new pickle
        file["date"] = [datetime.date.today()]
        file["seals"] = [seals]
        file.to_pickle('database/seals.pickle')

        print("Done refreshing seals.pickle")



class updateActivityDB(BaseEvent):
    def __init__(self):
        # Set the interval for this event
        interval_minutes = 60
        super().__init__(scheduler_type="interval", interval_minutes=interval_minutes)

    async def run(self, client):
        """
        This runs hourly and updates all the users infos,
        that are in one of the servers the bot is in.
        """
        print("Start Updating DB...")
        # todo enable again
        # destinyIDs = getAllDestinyIDs()
        #
        # # update all users
        # async for destinyID in getAllDestinyIDs(client, destinyIDs):
        #     await updateDB(destinyID)
        # print("Done Updating DB!")


# generator - get destinyIDs of eligible users
async def getDestinyIDs(client, destinyIDs):
    # get all users the bot shares a guild with
    shared_guild = []
    for guild in client.guilds:
        for members in guild:
            shared_guild.append(members.id)
    set(shared_guild)

    # loop though all ids
    for destinyID in destinyIDs:
        discordID = lookupDiscordID(destinyID)

        # check is user is in a guild with bot
        if not discordID in shared_guild:
            continue

        yield destinyID








