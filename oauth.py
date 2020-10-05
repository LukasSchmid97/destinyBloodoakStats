#!/usr/bin/python3

import requests, json
from static.config      import BUNGIE_OAUTH, BUNGIE_TOKEN, BUNGIE_SECRET, B64_SECRET, NEWTONS_WEBHOOK
from flask              import Flask, request, redirect, Response, send_file, render_template
from functions.database import insertToken, getRefreshToken
import asyncio
import aiohttp
import os
from flask import send_from_directory, url_for

async def refresh_token(discordID):
    url = 'https://www.bungie.net/platform/app/oauth/token/'
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'authorization': 'Basic ' + str(B64_SECRET)
    }
    refresh_token = getRefreshToken(discordID)

    data = 'grant_type=refresh_token&refresh_token=' + str(refresh_token)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers, allow_redirects=False) as r:
            data = await r.json()
            access_token = data['access_token']
            refresh_token = data['refresh_token']

            print('got new token ' + str(access_token))

            insertToken(discordID, None, None, access_token, refresh_token)


########################################## FLASK STUFF ##################################################
app = Flask(__name__)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/test')
def test():
    print('testing')
    return "hi"

@app.route('/level1')
@app.route('/level1/<highscore>')
def level1():
    highscore = request.cookies.get('userHighscore')
    return render_template('level1.html', highscore=highscore)

@app.route('/')
def root():
    print('called root')
    #print('got request')
    response = request.args
    if not (code := response.get('code', None)): #for user auth
        return redirect("http://www.elevatorbot.ch/reacttest/build", code=301)
    print(code)
    #print(f'code is {code}')
    (discordID,serverID) = response['state'].split(':') #mine

    url = 'https://www.bungie.net/platform/app/oauth/token/'
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'authorization': 'Basic '+ str(B64_SECRET) #unqiue to this app
    }

    data = f'grant_type=authorization_code&code={code}'

    r = requests.post(url, data=data, headers=headers)
    authresponse = r.json()
    access_token = authresponse['access_token']
    refresh_token = authresponse['refresh_token']

    #print(f'bungie responded {r.content} and the token is {access_token}')
    #membershipid = r.json()['membership_id']

    reqParams = {
        'Authorization': 'Bearer ' + str(access_token),
        'X-API-Key': BUNGIE_TOKEN
    }
    
    r = requests.get(url='https://www.bungie.net/platform/User/GetMembershipsForCurrentUser/', headers=reqParams)
    response = r.json()['Response']
    membershiplist = response['destinyMemberships']
    #print(membershiplist)
    primarymembership = None
    battlenetname = '_missing_'
    for membership in membershiplist:
        if int(membership["membershipType"]) == 3:
            battlenetname = membership["displayName"]
        if "crossSaveOverride" in membership.keys() and membership["crossSaveOverride"] and membership["membershipType"] != membership["crossSaveOverride"]:
            #print(f'membership {membership["membershipType"]} did not equal override {membership["crossSaveOverride"]}')
            continue
        primarymembership = membership
    
    if not primarymembership:
        print(f'no primary membership found for {battlenetname} aka {discordID} in server {serverID}')

    insertToken(int(discordID), int(primarymembership['membershipId']), int(serverID), access_token, refresh_token, force=True)
    print(f"<@{discordID}> registered with ID {primarymembership['membershipId']} and display name {primarymembership['LastSeenDisplayName']} Bnet-Name: {battlenetname}")
    webhookURL = NEWTONS_WEBHOOK
    requestdata = {
        'content': f"<@{discordID}> has ID {primarymembership['membershipId']} and display name {primarymembership['LastSeenDisplayName']} Bnet-Name: {battlenetname}",
        'username': 'EscalatorBot',
        "allowed_mentions": {
            "parse": ["users"],
            "users": []
        },
    }
    rp = requests.post(url=webhookURL, data=json.dumps(requestdata), headers={"Content-Type": "application/json"})
    return 'Thank you for signing up with <h1> Elevator Bot </h1>\n <p style="bottom: 20" >There will be cake</p>' # response to your request.



@app.route('/.well-known/acme-challenge/<challenge>')
def letsencrypt_check(challenge):
    challenge_response = {
        "<some_challenge_token>":"<challenge_response>",
        "<other_challenge_token>":"<challenge_response>"
    }
    return Response(challenge_response[challenge], mimetype='text/plain')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.before_request
def before_request():
    if request.url.startswith('http://'):
        return redirect(request.url.replace('http://', 'https://'), code=301)
    pass


@app.errorhandler(404)
def not_found(e):
    """Page not found."""
    return "page not founderino"

if __name__ == '__main__':
    print('server running')
    app.run(host= '0.0.0.0')


