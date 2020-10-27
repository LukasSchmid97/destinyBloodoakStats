import datetime
import os
import pickle

import pandas

from commands.base_command import BaseCommand
from functions.dataLoading import getPlayersPastPVE
from functions.database import lookupDestinyID
from functions.formating import embed_message

whisper_hashes = [74501540, 1099555105]

class whisperkills(BaseCommand):
    def __init__(self):
        description = f'Shows a leaderboard of kills in the whisper mission'
        params = []
        topic = "Destiny"
        super().__init__(description, params, topic)


    async def handle(self, params, message, client):
        if not os.path.exists('database/whisperKills.pickle'):
            file = [datetime.date.min, []]
        else:
            with open('database/whisperKills.pickle', "rb") as f:
                file = pickle.load(f)

        # check if data is a day old
        if file[0] < datetime.date.today():
            async with message.channel.typing():
                # refresh data
                data = pandas.DataFrame(columns=["member", "kills"])

                async for member in message.guild.fetch_members():
                    result = await self.handleUser(member)
                    if result:
                        data = data.append(result, ignore_index=True)


                data.sort_values(by=["kills"], inplace=True, ascending=False)
                data.reset_index(drop=True, inplace=True)

                file = [datetime.date.today(), data]

                with open('database/whisperKills.pickle', "wb") as f:
                    pickle.dump(file, f)

        ranking = []
        found = False
        for index, row in file[1].iterrows():
            if len(ranking) < 12:
                # setting a flag if user is in list
                if row["member"] == message.author.display_name:
                    found = True
                    ranking.append(
                        str(index + 1) + ") **[ " + row["member"] + " ]** _(Kills: " + str(int(row["kills"])) + ")_")
                else:
                    ranking.append(str(index + 1) + ") **" + row["member"] + "** _(Kills: " + str(int(row["kills"])) + ")_")

            # looping through rest until original user is found
            elif (len(ranking) >= 12) and (not found):
                # adding only this user
                if row["member"] == message.author.display_name:
                    ranking.append("...")
                    ranking.append(str(index + 1) + ") **" + row["member"] + "** _(Kills: " + str(int(row["kills"])) + ")_")
                    break

            else:
                break

        await message.channel.send(embed=embed_message(
            'Top Guardians by D2 Whisper Mission Kills',
            "\n".join(ranking)
        ))

    async def handleUser(self, member):
        destinyID = lookupDestinyID(member.id)

        if not destinyID:
            return False

        entry = {
            'member': member.display_name,
            'kills': 0
        }

        async for activity in getPlayersPastPVE(destinyID):
            # whisper mission hash
            if activity["activityDetails"]["referenceId"] in whisper_hashes:
                number_of_kills = float(activity["values"]["kills"]["basic"]["value"])
                entry["kills"] += number_of_kills

        return entry
