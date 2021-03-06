from commands.base_command import BaseCommand
from functions.dataLoading import getNameAndCrossaveNameToHashMapByClanid
from functions.database import lookupDiscordID
from static.dict import clanids


class getUserMatching(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "[dev] match ingame and Discord names"
        params = []
        topic = "Registration"
        super().__init__(description, params, topic)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, mentioned_user, client):
        
        for clanid,name in clanids.items():
            await message.channel.send(f'matching members for clan {name}')
            clanmap = await getNameAndCrossaveNameToHashMapByClanid(clanid)
            successfulMatches = []
            unsuccessfulMatches = []
            for userid, (steamname, crosssavename) in clanmap.items():
                discordID = lookupDiscordID(userid)
                if discordID:
                    # user could be matched
                    guy = client.get_user(discordID)
                    if guy:
                        successfulMatches.append((steamname, crosssavename, guy.name))
                    else:
                        await message.channel.send(f'[ERROR] {steamname}/{crosssavename} with destinyID {userid} has discordID {discordID} but it is faulty')
                else:
                    # user not found
                    unsuccessfulMatches.append((steamname, crosssavename, userid))

            await message.channel.send('SUCCESSFUL MATCHES:')
            sortedSuccessfulMatches = sorted(successfulMatches, key=lambda pair: pair[2].lower())
            successfulMessage = ''
            for (steamname, crosssavename, username) in sortedSuccessfulMatches:  
                successfulMessage += f'{username:<30} - {steamname} / {crosssavename}\n'
            
            if len(successfulMessage) < 2000:
                await message.channel.send(successfulMessage)
            else:
                remainingMessage = successfulMessage
                while curMessage := remainingMessage[:1900]:
                    await message.channel.send(curMessage)
                    remainingMessage = remainingMessage[1900:]
            await message.channel.send('FAILED MATCHES:')
            unsuccessfulMessage = ''
            for (steamname, crosssavename, userid) in unsuccessfulMatches:    
                unsuccessfulMessage += f'{steamname} / {crosssavename} (Steam-ID {userid}) could not be found in Discord \n'  
            
            if unsuccessfulMessage:
                await message.channel.send(unsuccessfulMessage)
            else:
                await message.channel.send('No unsuccessful matches <:PogU:670369128237760522>')