from commands.base_command import BaseCommand
from functions.roles import hasAdminOrDevPermissions

import re
import discord
import matplotlib.pyplot as plt
import os

class statistic(BaseCommand):
    def __init__(self):
        # A quick description for the help tmessage
        description = "[dev] shows various statistics"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        if not await hasAdminOrDevPermissions(message):
            return

        if params[0] == "emotes":
            a = await message.channel.send("Working, will take a while...")
            async with message.channel.typing():
                emotes = await message.guild.fetch_emojis()
                channels = await message.guild.fetch_channels()

                count = {}

                for channel in channels:
                    if channel.type == discord.ChannelType.text:
                        async for msg in channel.history():
                            if not message.author.bot:
                                for reaction in msg.reactions:
                                    if isinstance(reaction.emoji, str):
                                        try:
                                            count[reaction.emoji] += 1
                                        except KeyError:
                                            count.update({reaction.emoji: 1})
                                    else:
                                        try:
                                            count[reaction.emoji.name] += 1
                                        except KeyError:
                                            count.update({reaction.emoji.name: 1})

                                for emote in emotes:
                                    if f"<:{emote.name}:{emote.id}>" in msg.content:
                                        try:
                                            count[emote.name] += len(re.findall(f"<:{emote.name}:{emote.id}>", msg.content))
                                        except KeyError:
                                            count.update({emote.name: len(re.findall(f"<:{emote.name}:{emote.id}>", msg.content))})

            print(count)
            keys = count.keys()
            values = count.values()

            plt.bar(keys, values)
            plt.title("Descend Emote Usage", fontweight="bold", size=20)
            plt.xticks(rotation=90)
            plt.tight_layout()

            plt.savefig('emote_usage.png')


            # send the sorted list
            sort = {k: v for k, v in sorted(count.items(), key=lambda item: item[1], reverse=True)}
            text = []
            i = 1
            for k, v in sort.items():
                text.append(f"{i}) `{k}` - Count: {v}\n")
                i += 1

            msgs = []
            msg = ""
            for e in text:
                if len(msg + e) < 2000:
                    msg += e
                else:
                    msgs.append(msg)
                    msg = e
            msgs.append(msg)


            await a.delete()
            await message.channel.send("__**Emote Usage**__")
            for msg in msgs:
                await message.channel.send(msg)

            # sending them the file
            await message.channel.send(file=discord.File('emote_usage.png'))

            # delete file
            os.remove('emote_usage.png')



