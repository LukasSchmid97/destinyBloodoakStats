from functions.formating import embed_message
from functions.database import insertBountyUser, getBountyUserList, getLevel, addLevel, setLevel, lookupDestinyID, lookupServerID
from functions.bounties.boutiesBountyRequirements import bounties, competition_bounties
from functions.bounties.bountiesBackend import formatLeaderboardMessage, returnLeaderboard, getCompetitionBountiesLeaderboards, changeCompetitionBountiesLeaderboards, experiencePvp, experiencePve, experienceRaids, threadingCompetitionBounties, threadingBounties

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
    # award points for the competition bounties
    awardCompetitionBountiesPoints()

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


# awards points to whoever has the most points. Can be multiple people if tied
def awardCompetitionBountiesPoints():
    leaderboards = getCompetitionBountiesLeaderboards()

    # loop through topic, then though users
    for topic in leaderboards:
        for discordID in leaderboards[topic]:

            # award the points in the respective categories
            addLevel(leaderboards[topic][discordID], f"points_competition_{topic.lower()}", discordID)

    # delete now old leaderboards
    if os.path.exists('functions/bounties/competitionBountiesLeaderboards.pickle'):
        os.remove('functions/bounties/competitionBountiesLeaderboards.pickle')


# print the bounties in their respective channels
async def displayBounties(client):
    # load bounties
    with open('functions/bounties/currentBounties.pickle', "rb") as f:
        json = pickle.load(f)

    # get channel and guild id
    with open('functions/bounties/channelIDs.pickle', "rb") as f:
        file = pickle.load(f)

    # get the users that signed up for notifications
    text = ["⁣"]    # so that it still works even with nobody signed up
    for discordID in getBountyUserList():
        if getLevel("notifications", discordID) == 1:
            text.append(f"<@{discordID}>")

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
                        embed.add_field(name=f"{experience}:", value=f"{name} (Points: {req['points']})\n⁣", inline=False)
                    await bounties_channel.send(embed=embed)

                # ping users
                msg = await bounties_channel.send(" ".join(text))
                await msg.delete()

                print("Updated bounty display")

            if "competition_bounties_channel" in file:
                await displayCompetitionBounties(client, guild)

                # ping users
                msg = await discord.utils.get(guild.channels, id=file["competition_bounties_channel"]).send(" ".join(text))
                await msg.delete()

            print("Done updating displays")


async def displayCompetitionBounties(client, guild, message=None):
    # load channel ids
    with open('functions/bounties/channelIDs.pickle', "rb") as f:
        file = pickle.load(f)

    # load bounties
    with open('functions/bounties/currentBounties.pickle', "rb") as f:
        json = pickle.load(f)

    # load leaderboards
    leaderboards = getCompetitionBountiesLeaderboards()

    # get channel id and clear channel
    competition_bounties_channel = discord.utils.get(guild.channels, id=file["competition_bounties_channel"])
    if not message:
        await competition_bounties_channel.purge(limit=100)

    for topic in json["competition_bounties"].keys():
        name, req = list(json["competition_bounties"][topic].items())[0]
        embed = embed_message(
            topic,
            f"{name} (Points: {req['points']})\n⁣"
        )

        # read the current leaderboard and display the top x = 10 players
        ranking = []
        try:
            i = 1
            for discordID, value in leaderboards[topic].items():
                ranking.append(str(i) + ") **" + client.get_user(discordID).display_name + "** _(Score: " + str(value) + ")_")
                # break after x entries
                i += 1
                if i > 10:
                    break
        except KeyError:
            pass

        embed.add_field(name=f"Current Leaderboard:", value=f"\n".join(ranking) if ranking else "Nobody has completed this yet", inline=False)

        # edit msg if given one, otherwise create a new one and save the id
        if message:
            # gets the msg object related to the current topic in the competition_bounties_channel
            message = await discord.utils.get(guild.channels, id=file["competition_bounties_channel"]).fetch_message(file[f"competition_bounties_channel_{topic.lower()}_message_id"])
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

            # update the leaderboard file
            changeCompetitionBountiesLeaderboards(topic, leaderboard)

            # display the new leaderboards
            await displayCompetitionBounties(client, guild, message=True)

    # update the big leaderboard
    await displayLeaderboard(client)


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


# updates the leaderboard display
async def displayLeaderboard(client, use_old_message=True):
    # function to condense leaderboards
    def condense(lead_big, lead_new):
        for id, value in lead_new.items():
            if value is not None:
                if id in lead_big:
                    lead_big.update({id: (0 if lead_big[id] is None else value) + value})
                else:
                    lead_big.update({id: value})

    # get current leaderboards and condense them into one
    leaderboard = {}
    condense(leaderboard, returnLeaderboard("points_bounties_raids"))
    condense(leaderboard, returnLeaderboard("points_bounties_pve"))
    condense(leaderboard, returnLeaderboard("points_bounties_pvp"))
    condense(leaderboard, returnLeaderboard("points_competition_raids"))
    condense(leaderboard, returnLeaderboard("points_competition_pve"))
    condense(leaderboard, returnLeaderboard("points_competition_pvp"))

    # format that
    ranking = await formatLeaderboardMessage(client, leaderboard)

    # load ids
    with open('functions/bounties/channelIDs.pickle', "rb") as f:
        file = pickle.load(f)

    # try to get the leaderboard message id, else make a new message
    message_id = None
    try:
        message_id = file["leaderboard_channel_message_id"]
    except:
        pass

    for guild in client.guilds:
        if guild.id == file["guild_id"]:

            # get the channel id
            competition_bounties_channel = discord.utils.get(guild.channels, id=file["leaderboard_channel"])

            embed = embed_message(
                "Leaderboard",
                (f"\n".join(ranking)) if ranking else "Nobody has any points yet",
                footer="This leaderboard will update every ~60 minutes"
            )

            if message_id and use_old_message:
                # get the leaderboard msg object
                message = await discord.utils.get(
                        guild.channels,
                        id=file["leaderboard_channel"]
                    ).fetch_message(file["leaderboard_channel_message_id"])

                await message.edit(embed=embed)
            else:
                await competition_bounties_channel.purge(limit=100)
                msg = await competition_bounties_channel.send(embed=embed)
                saveAsGlobalVar("leaderboard_channel_message_id", msg.id)

    print("Updated Leaderboard")


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
                            f'If you want to register to the **Bounty Goblins**, react with <:register:751774620696313966> \n\n If you want to receive a notification whenever new bounties are available, react with <a:notifications:751771924866269214>'
                        ))
                        register = client.get_emoji(751774620696313966)
                        await msg.add_reaction(register)
                        notification = client.get_emoji(751771924866269214)
                        await msg.add_reaction(notification)
                        saveAsGlobalVar("register_channel_message_id", msg.id)

                # if "tournament_channel" in file:
                #     channel = discord.utils.get(guild.channels, id=file["tournament_channel"])
                #     await channel.send("tournament_channel")


async def registrationMessageReactions(client, user, emoji, register_channel, register_channel_message_id):
    message = await register_channel.fetch_message(register_channel_message_id)

    register = client.get_emoji(751774620696313966)
    notification = client.get_emoji(751771924866269214)

    if emoji.id == register.id:
        await message.remove_reaction(register, user)
        # register him
        if user.id not in getBountyUserList():
            insertBountyUser(user.id)
            setLevel(1, "active", user.id)
            await updateAllExperience(client, user.id, new_register=True)
        elif getLevel("active", user.id) != 1:
            setLevel(1, "active", user.id)
            await updateAllExperience(client, user.id, new_register=True)

        # unregister him
        else:
            setLevel(0, "active", user.id)
            setLevel(0, "notifications", user.id)
            embed = embed_message(
                "See you",
                "You are no longer signed up with the **Bounty Goblins**"
                )
            await user.send(embed=embed)

    elif emoji.id == notification.id:
        await message.remove_reaction(notification, user)
        # you can only sign up if registered
        if user.id in getBountyUserList():
            if getLevel("active", user.id) == 1:
                status = getLevel("notifications", user.id)
                setLevel(0 if status == 1 else 1, "notifications", user.id)

                text = "now " if status == 0 else "no longer "
                embed = embed_message(
                    "Notifications",
                    f"You are {text}receiving notifications when new bounties are available!"
                )
                await user.send(embed=embed)

    print(f"Handled {user.display_name}'s request")


# loop though all users and refresh their experience level. Get's called once a week on sunday at midnight
async def updateExperienceLevels(client):
    for user in getBountyUserList():
        await updateAllExperience(client, user)


# updates / sets all experience levels for the user
async def updateAllExperience(client, discordID, new_register=False):
    # get user info
    destinyID = lookupDestinyID(discordID)
    user = client.get_user(discordID)

    # get levels at the start, update levels and get the new ones
    pre_pve = getLevel("exp_pve", user.id)
    pre_pvp = getLevel("exp_pvp", user.id)
    pre_raids = getLevel("exp_raids", user.id)
    experiencePve(destinyID)
    experiencePvp(destinyID)
    experienceRaids(destinyID)
    post_pve = getLevel("exp_pve", user.id)
    post_pvp = getLevel("exp_pvp", user.id)
    post_raids = getLevel("exp_raids", user.id)

    embed = None
    # message the user if they newly registered
    if new_register:
        embed = embed_message(
            "Your Experience Levels",
            f"Thanks for registering with the **Bounty Goblins**. \n Depending on your experience levels, you will only get credit for completing the respective bounties in the respective categories. \n\n Your experience levels are:"
        )

    # message the user if levels have changed
    elif not (pre_pve == post_pve and pre_pvp == post_pvp and pre_raids and post_raids):
        embed = embed_message(
            "Your Experience Levels",
            f"Some of your experience levels have recently changed. \n As a reminder, depending on your experience levels, you will only get credit for completing the respective bounties in the respective categories. \n\n Your experience levels are:"
        )

    try:
        embed.add_field(name="Raids Experience", value="Experienced Player" if post_raids == 1 else "New Player",
                        inline=True)
        embed.add_field(name="Pve Experience", value="Experienced Player" if post_pve == 1 else "New Player",
                        inline=True)
        embed.add_field(name="PvP Experience", value="Experienced Player" if post_pvp == 1 else "New Player",
                        inline=True)
    except AttributeError:  # meaning not new and nothing changed
        pass

    if embed:
        await user.send(embed=embed)

