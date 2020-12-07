from commands.base_command import BaseCommand
from functions.roles import assignRolesToUser, removeRolesFromUser
from static.globals import muted_role_id

import asyncio


class startCounting(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "Starts the counting challenge"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        await message.channel.send("Start counting, first person has to begin with 1")

        i = 1
        while True:
            # wait for the next message in the channel
            def check(m):
                return m.channel == message.channel
            msg = await client.wait_for('message', check=check)

            # check if he counted up correctly
            if msg.content != str(i):
                await message.channel.send(f"{msg.author.mention} ruined it at {str(i-1)} and thus got muted for 5 minutes <:SadChamp:670672093263822877>")
                await assignRolesToUser([muted_role_id], msg.author, msg.guild)
                await asyncio.sleep(60 * 5)
                await removeRolesFromUser([muted_role_id], msg.author, msg.guild)
                return

            i += 1
