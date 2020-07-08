from commands.base_command  import BaseCommand
import os
from static.config import BUNGIE_OAUTH
from static.dict import clanids
from functions.database import insertUser, removeUser, lookupDestinyID, lookupDiscordID
from functions.formating import embed_message
from functions.network import getJSONfromURL
import discord

class getDestinyID(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] check a user's destinyID"
        params = ['User']
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        discordID = int(params[0])
        discordUser = client.get_user(discordID)
        if not discordUser:
             await message.channel.send(f'Unknown User {discordID}')
        print(f'{discordID} with {lookupDestinyID(discordID)}')
        await message.channel.send(f'{discordUser.name} has destinyID {lookupDestinyID(discordID)}')


class getDiscordID(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] check a user's discordID by destinyID"
        params = ['User']
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        destinyID = int(params[0])
        print(f'{destinyID} with {lookupDiscordID(destinyID)}')
        await message.channel.send(f'{destinyID} has discordID {lookupDiscordID(destinyID)}')

class getDiscordFuzzy(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] check a user's discordID by destinyID"
        params = ['partial name']
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        partialName = params[0]
        clansearch = []
        for clanid in clanids:
            returnjson = getJSONfromURL(f"https://www.bungie.net/Platform/GroupV2/{clanid}/Members?nameSearch={partialName}")
            clansearch.append(returnjson)

        embed = discord.Embed(title=f'Possible matches for {partialName}:')

        for result in clansearch:
            resp = result['Response']
            for user in resp['results']:
                ingamename = user['destinyUserInfo']['LastSeenDisplayName']
                destinyID = user['destinyUserInfo']['membershipId']
                discordID = lookupDiscordID(destinyID)
                embed.add_field(name=ingamename, value=f"<@{discordID}>", inline=False)

        await message.channel.send(embed=embed)