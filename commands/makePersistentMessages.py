from commands.base_command  import BaseCommand
from functions.bounties.bountiesBackend import saveAsGlobalVar, deleteFromGlobalVar
from functions.persistentMessages import persistentChannelMessages
from functions.roles                import assignRolesToUser, removeRolesFromUser

import discord


# writes the message the user will see and react to and saves the id in the pickle
class makeChannelOtherGameRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] make channel for getting other game roles. will delete all msg in channel if used"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        # add channel id to pickle where bounty channel ids are also saved
        deleteFromGlobalVar("other_game_roles_channel_message_id")
        saveAsGlobalVar("other_game_roles_channel", message.channel.id, message.guild.id)
        await persistentChannelMessages(client)


# assign the roles. get's called from bloodbot.py
async def otherGameRolesMessageReactions(client, user, emoji, register_channel, channel_message_id):
    message = await register_channel.fetch_message(channel_message_id)

    # emoji ids
    among_us = client.get_emoji(751020830376591420)
    barotrauma = client.get_emoji(756077724870901830)
    gta = client.get_emoji(751020831382962247)
    valorant = client.get_emoji(751020830414209064)
    lol = client.get_emoji(756076309527920661)

    # role ids
    amongUs_id = 750409552075423753
    barotrauma_id = 738438622553964636
    gta_id = 709120893728718910
    valorant_id = 709378171832893572
    lol_id = 756076447881363486

    # get current roles
    roles = [role.id for role in user.roles]

    # remove reaction and apply role
    if emoji == among_us:
        if amongUs_id not in roles:
            await user.add_roles(discord.utils.get(message.guild.roles, id=amongUs_id))
        else:
            await user.remove_roles(discord.utils.get(message.guild.roles, id=amongUs_id))
        await message.remove_reaction(among_us, user)

    elif emoji == barotrauma:
        if barotrauma_id not in roles:
            await user.add_roles(discord.utils.get(message.guild.roles, id=barotrauma_id))
        else:
            await user.remove_roles(discord.utils.get(message.guild.roles, id=barotrauma_id))
        await message.remove_reaction(barotrauma, user)

    elif emoji == gta:
        if gta_id not in roles:
            await user.add_roles(discord.utils.get(message.guild.roles, id=gta_id))
        else:
            await user.remove_roles(discord.utils.get(message.guild.roles, id=gta_id))
        await message.remove_reaction(gta, user)

    elif emoji == valorant:
        if valorant_id not in roles:
            await user.add_roles(discord.utils.get(message.guild.roles, id=valorant_id))
        else:
            await user.remove_roles(discord.utils.get(message.guild.roles, id=valorant_id))
        await message.remove_reaction(valorant, user)

    elif emoji == lol:
        if lol_id not in roles:
            await user.add_roles(discord.utils.get(message.guild.roles, id=lol_id))
        else:
            await user.remove_roles(discord.utils.get(message.guild.roles, id=lol_id))
        await message.remove_reaction(lol, user)


# writes the message the user will see and react to and saves the id in the pickle
class makeChannelClanJoinRequest(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] make channel for getting other game roles. will delete all msg in channel if used"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        # add channel id to pickle where bounty channel ids are also saved
        deleteFromGlobalVar("clan_join_request_channel_message_id")
        saveAsGlobalVar("clan_join_request_channel", message.channel.id, message.guild.id)
        await persistentChannelMessages(client)


# writes the message the user will see and react to and saves the id in the pickle
class makeChannelReadRules(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] make channel for accepting the rules"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        # add channel id to pickle where bounty channel ids are also saved
        deleteFromGlobalVar("read_rules_channel_message_id")
        saveAsGlobalVar("read_rules_channel", message.channel.id, message.guild.id)
        await persistentChannelMessages(client)


# assign the role. get's called from bloodbot.py
async def readRulesMessageReactions(client, user, emoji, register_channel, channel_message_id):
    message = await register_channel.fetch_message(channel_message_id)
    emote = client.get_emoji(768908985557844028)
    role_id = 769612980978843668

    if emoji == emote:
        await message.remove_reaction(emote, user)

        # adds the read rules role to the user
        await assignRolesToUser([role_id], user, message.guild)

        # removes the guest role
        await removeRolesFromUser(["Guest"], user, message.guild)
