from functions.formating import embed_message
from functions.database import insertBountyUser, removeBountyUser, getBountyUserList, getLevel
from functions.bounties.boutiesBountyRequirements import bounties, competition_bounties
from functions.bounties.bountiesBackend import updateAllExperience, threadingCompetitionBounties, threadingBounties

import os
import pickle
import discord
import random
import json
import asyncio
import datetime
import concurrent.futures



# randomly generate bounties. One per topic for both of the lists
def generateBounties(client):
    # looping though the bounties and generating random ones
    file = {}
    file["bounties"] = {}
    for topic in bounties.keys():
        file["bounties"][topic] = {}
        for experience in bounties[topic].keys():
            key, value = random.choice(list(bounties[topic][experience].items()))

            # if "randomActivity" is present, get a random activity from the list and delete "randomActivity" so it doesn't take up space anymore
            if "randomActivity" in value:
                value["allowedActivities"] = [random.choice(value.pop("randomActivity"))]
                value["requirements"].pop(value["requirements"].index("randomActivity"))
                value["requirements"].append("allowedActivities")

            file["bounties"][topic][experience] = {}
            file["bounties"][topic][experience][key] = value

    # looping though the competition bounties and generating random ones
    file["competition_bounties"] = {}
    for topic in competition_bounties.keys():
        key, value = random.choice(list(competition_bounties[topic].items()))

        # if "randomActivity" is present, get a random activity from the list and delete "randomActivity" so it doesn't take up space anymore
        if "randomActivity" in value:
            value["allowedActivities"] = [random.choice(value.pop("randomActivity"))]
            value["requirements"].pop(value["requirements"].index("randomActivity"))
            value["requirements"].append("allowedActivities")

        file["competition_bounties"][topic] = {}
        file["competition_bounties"][topic][key] = value

    # add current time to list
    file["time"] = str(datetime.datetime.now())

    # overwrite the old bounties
    with open('functions/bounties/currentBounties.pickle', "wb") as f:
        pickle.dump(file, f)

    print("Generated new bounties:")
    print(json.dumps(file, indent=4))

    # update the display
    task = displayBounties(client)
    asyncio.run_coroutine_threadsafe(task, client.loop)

    # delete old bounty completion tracking pickle
    if os.path.exists('functions/bounties/playerBountyStatus.pickle'):
        os.remove('functions/bounties/playerBountyStatus.pickle')

    # todo add score to users who won the competitive bounties


# print the bounties in their respective channels
async def displayBounties(client):
    # load bounties
    with open('functions/bounties/currentBounties.pickle', "rb") as f:
        json = pickle.load(f)

    # get channel and guild id
    with open('functions/bounties/channelIDs.pickle', "rb") as f:
        file = pickle.load(f)
    for guild in client.guilds:
        if guild.id == file["guild_id"]:

            # clean channels and call the actual print function
            if "bounties_channel" in file:
                bounties_channel = discord.utils.get(guild.channels, id=file["bounties_channel"])
                await bounties_channel.purge(limit=100)
                for topic in json["bounties"].keys():
                    embed = embed_message(
                        topic
                    )
                    for experience in json["bounties"][topic].keys():
                        name, req = list(json["bounties"][topic][experience].items())[0]
                        embed.add_field(name=f"{experience}:", value=f"{name} (Points: {req['points']})", inline=False)
                    await bounties_channel.send(embed=embed)
                print("Updated bounty display")
            if "competition_bounties_channel" in file:
                await displayCompetitionBounties(guild, file)

    print("Done updating displays")


async def displayCompetitionBounties(guild, file, leaderboard=None, message=None):
    # load bounties
    with open('functions/bounties/currentBounties.pickle', "rb") as f:
        json = pickle.load(f)

    competition_bounties_channel = discord.utils.get(guild.channels, id=file["competition_bounties_channel"])
    await competition_bounties_channel.purge(limit=100)
    for topic in json["competition_bounties"].keys():
        name, req = list(json["competition_bounties"][topic].items())[0]
        embed = embed_message(
            topic,
            f"{name} (Points: {req['points']})"
        )

        # if the leaderboard already exists, add it to the msg
        if leaderboard:
            embed.add_field(name="Current Leaderboard:", value=f"\n".join(leaderboard), inline=False)

        # edit msg if given one, otherwise create a new one and save the id
        if message:
            await message.edit(embed=embed)
        else:
            msg = await competition_bounties_channel.send(embed=embed)
            saveAsGlobalVar(f"competition_bounties_channel_{topic.lower()}_message_id", msg.id)
    print("Updated competition bounty display")


# checks if any player has completed a bounty
async def bountyCompletion(client):
    # load bounties
    with open('functions/bounties/currentBounties.pickle', "rb") as f:
        bounties = pickle.load(f)
    cutoff = datetime.datetime.strptime(bounties["time"], "%Y-%m-%d %H:%M:%S.%f")

    # load channel ids
    with open('functions/bounties/channelIDs.pickle', "rb") as f:
        file = pickle.load(f)
        for guild in client.guilds:
            if guild.id == file["guild_id"]:
                break

    # loop though all registered users
    with concurrent.futures.ThreadPoolExecutor(os.cpu_count() * 5) as pool:
        futurelist = [pool.submit(threadingBounties, bounties["bounties"], cutoff, user) for user in getBountyUserList()]

        for future in concurrent.futures.as_completed(futurelist):
            try:
                result = future.result()
            except Exception as exc:
                print(f'generated an exception: {exc}')


    # loop though all the competition bounties
    for topic in bounties["competition_bounties"]:
        for bounty in bounties["competition_bounties"][topic]:

            # gets the msg object related to the current topic in the competition_bounties_channel
            message = await discord.utils.get(client.guild.channels, id=file["competition_bounties_channel"]).fetch_message(file[f"competition_bounties_channel_{topic.lower()}_message_id"])

            # create leaderboard dict
            leaderboard = {}

            # loop though all registered users
            with concurrent.futures.ThreadPoolExecutor(os.cpu_count() * 5) as pool:
                futurelist = [pool.submit(threadingCompetitionBounties, bounties["competition_bounties"][topic][bounty], cutoff, user.id)
                              for user in getBountyUserList()]

                for future in concurrent.futures.as_completed(futurelist):
                    try:
                        result = future.result()
                        leaderboard.update(result)
                    except Exception as exc:
                        print(f'generated an exception: {exc}')

            # sort leaderboard
            leaderboard = {k: v for k, v in sorted(leaderboard.items(), key=lambda item: item[1], reverse=True)}

            # update bounty leaderboard
            ranking = []
            i = 1
            for key, value in leaderboard.items():
                ranking.append(str(i) + ") **" + client.get_user(key).display_name + "** _(Score: " + str(value) + ")_")

                # break after 10 entries
                i += 1
                if i > 10:
                    break

            await displayCompetitionBounties(guild, file, ranking, message)


def startTournament():
    #todo
    pass


def saveAsGlobalVar(name, value, guild_id = None):
    if not os.path.exists('functions/bounties/channelIDs.pickle'):
        file = {}
    else:
        with open('functions/bounties/channelIDs.pickle', "rb") as f:
            file = pickle.load(f)

    if guild_id:
        file["guild_id"] = guild_id
    file[name] = value

    with open('functions/bounties/channelIDs.pickle', "wb") as f:
        pickle.dump(file, f)


def deleteFromGlobalVar(name):
    if os.path.exists('functions/bounties/channelIDs.pickle'):
        with open('functions/bounties/channelIDs.pickle', "rb") as f:
            file = pickle.load(f)

        try:
            file.pop(name)
        except:
            pass

        with open('functions/bounties/channelIDs.pickle', "wb") as f:
            pickle.dump(file, f)


# todo: add leaderboard lookup and calculation
def leaderboardMessage():

    embed = embed_message(
        f'Leaderboard',
        f'ToDo',
        f"The leaderboard will update every 60 minutes"
    )

    return embed


async def updateLeaderboard(client):
    with open('functions/bounties/channelIDs.pickle', "rb") as f:
        file = pickle.load(f)

    for guild in client.guilds:
        if guild.id == file["guild_id"]:
            embed = leaderboardMessage()
            channel = discord.utils.get(guild.channels, id=file["leaderboard_channel"])

            if "leaderboard_channel_message_id" not in file:
                msg = await channel.send(embed=embed)
                saveAsGlobalVar("leaderboard_channel_message_id", msg.id)

            else:
                msg = await channel.fetch_message(file["leaderboard_channel_message_id"])
                await msg.edit(embed=embed)

            return


# writes the message the user will see and react to and saves the id in the pickle
async def bountiesChannelMessage(client):
    if os.path.exists('functions/bounties/channelIDs.pickle'):
        with open('functions/bounties/channelIDs.pickle', "rb") as f:
            file = pickle.load(f)

        for guild in client.guilds:
            if guild.id == file["guild_id"]:

                # the other games role channel message
                if "other_game_roles_channel" in file:
                    if "other_game_roles_channel_message_id" not in file:
                        channel = discord.utils.get(guild.channels, id=file["other_game_roles_channel"])
                        await channel.purge(limit=100)

                        # send register msg and save the id
                        msg = await channel.send(embed=embed_message(
                            f'Other Game Roles',
                            f'React to add / remove other game roles'
                        ))

                        among_us = client.get_emoji(751020830376591420)
                        barotrauma = client.get_emoji(751022749773856929)
                        gta = client.get_emoji(751020831382962247)
                        valorant = client.get_emoji(751020830414209064)

                        await msg.add_reaction(among_us)
                        await msg.add_reaction(barotrauma)
                        await msg.add_reaction(gta)
                        await msg.add_reaction(valorant)

                        saveAsGlobalVar("other_game_roles_channel_message_id", msg.id)

                # put message in #register channel if there is none
                if "register_channel" in file:
                    if "register_channel_message_id" not in file:
                        channel = discord.utils.get(guild.channels, id=file["register_channel"])
                        await channel.purge(limit=100)

                        # send register msg and save the id
                        msg = await channel.send(embed=embed_message(
                            f'Registration',
                            f'Please react if you want to register to the bounty program'
                        ))
                        await msg.add_reaction("✅")
                        await msg.add_reaction("❎")
                        saveAsGlobalVar("register_channel_message_id", msg.id)

                if "leaderboard_channel" in file:
                    if "leaderboard_channel_message_id" not in file:
                        channel = discord.utils.get(guild.channels, id=file["leaderboard_channel"])
                        await channel.purge(limit=100)

                        # send leaderboard msg
                        await updateLeaderboard(client)



                # if "tournament_channel" in file:
                #     channel = discord.utils.get(guild.channels, id=file["tournament_channel"])
                #     await channel.send("tournament_channel")

async def registrationMessageReactions(user, emoji, register_channel, register_channel_message_id):
    message = await register_channel.fetch_message(register_channel_message_id)

    if emoji.name == "✅":
        await message.remove_reaction("✅", user)
        await user.send("you signed up")
        insertBountyUser(user.id)
        updateAllExperience(user.id)



        pve = getLevel("exp_pve", user.id)
        pvp = getLevel("exp_pvp", user.id)
        raids = getLevel("exp_raids", user.id)
        await user.send(f"pve: {pve}, pvp: {pvp}, raids: {raids} ")

    elif emoji.name == "❎":
        await message.remove_reaction("❎", user)
        removeBountyUser(user.id)
        await user.send("you're no longer signed up")


#todo maybe another msg that you can react to to get pinged if new bouinties are there


# loop though all users and refresh their experience level. Get's called once a week on sunday at midnight
def updateExperienceLevels(client):
    for user in getBountyUserList():
        updateAllExperience(user)



