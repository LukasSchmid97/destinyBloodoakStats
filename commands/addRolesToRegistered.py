from commands.base_command  import BaseCommand
from functions.roles        import assignRolesToUser, removeRolesFromUser
from functions.database     import getToken
from functions.roles import hasAdminOrDevPermissions



class addRolesToRegistered(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "Assigns @Registered or @Not Registered to everyone"
        topic = "Registration"
        params = []
        super().__init__(description, params, topic)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        if not await hasAdminOrDevPermissions(message):
            return
        await message.channel.send("Working...")
        for member in message.guild.members:
            await removeRolesFromUser(["Registered"], member, message.guild)
            await removeRolesFromUser(["Not Registered"], member, message.guild)

            if getToken(member.id):
                await assignRolesToUser(["Registered"], member, message.guild)
                await message.channel.send(f"add @Registered to {member.name}")
            else:
                await assignRolesToUser(["Not Registered"], member, message.guild)
                await message.channel.send(f"add @Not Registered to {member.name}")

        await message.channel.send("Done")


class whoIsNotRegistered(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "Blames ppl who are not registered"
        topic = "Registration"
        params = []
        super().__init__(description, params, topic)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        people = []
        for member in message.guild.members:
            if not getToken(member.id):
                people.append(member.name)

        await message.channel.send(", ".join(people))