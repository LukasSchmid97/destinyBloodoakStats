#library imports
import os, pandas, xlsxwriter
import pandas.io.formats.excel
import concurrent.futures

from functions.dataLoading  import getNameToHashMapByClanid
from functions.roles        import getPlayerRoles
from static.dict            import requirementHashes, clanids


async def createSheet():
    #defining where and how to save the excel file
    path = os.path.dirname(os.path.abspath(__file__))
    path += '\\clanAchievementsShort.xlsx'
    writer = pandas.ExcelWriter(path, engine='xlsxwriter')

    #generating a statssheet for every clan in dict.clanids
    for clanid, clanname in clanids.items():
        memberids = await getNameToHashMapByClanid(clanid)
        userRoles = {}
        #Collects all roles in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            print(f'collecting data for {clanname}...')
            for key, value in memberids.items():
                for username, (t1,t2) in zip(key, await getPlayerRoles(value)):
                    userRoles[username] = t1 + t2
            print(f'done collecting for {clanname}')

        #list of all possible roles (defined in dict.requirementHashes)
        rolelist = []
        for _, yd in requirementHashes.items():
            rolelist += sorted(yd.keys())

        #generates the output table with user-to-earnedRoles mapping
        table = {}
        for username in memberids.keys():
            table[username] = []
            for role in rolelist:
                if role in userRoles[username]:
                    table[username].append('+')
                else:
                    table[username].append('-')
        

        #turns table into an excel
        df = pandas.DataFrame()
        df = df.from_dict(table, orient='index')
        df.sort_index(inplace=True)
        
        sheetname = clanname + ' Roles'
        df.to_excel(writer, header=False, startrow=1, sheet_name = sheetname)
        workbook  = writer.book
        worksheet = writer.sheets[sheetname]
        for idx, val in enumerate(rolelist):
            worksheet.write(0, idx+1, val)

    print('generating sheets...')

    workbook = writer.book

    #creating red/green background
    redBG = workbook.add_format({'bg_color': '#FFC7CE'})
    greenBG = workbook.add_format({'bg_color': '#C6EFCE'})

    #setting up vertical column headers
    verticalRole = workbook.add_format({'bold': True, 'rotation': 90})

    for worksheet in writer.sheets.values():
        #setting column rotation and widths
        worksheet.set_landscape()
        worksheet.set_row(0, None, verticalRole)
        worksheet.set_column(0, 0, 10)
        worksheet.set_column(1, 100, 3)

        #marking owned roles (+) green and unowned (-) red, adapts to manual changes
        worksheet.conditional_format("A2:DZ125", {'type': 'text',
                                                    'criteria': 'containing',
                                                    'value': '-',
                                                    'format': redBG})
        worksheet.conditional_format("A2:DZ125", {'type': 'text',
                                                    'criteria': 'containing',
                                                    'value': '+',
                                                    'format': greenBG})
    writer.save()

    print('excel file created')
    return path
