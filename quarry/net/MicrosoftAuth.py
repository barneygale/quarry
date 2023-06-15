import urllib.parse
import requests
import re
import json

CLIENT_ID = "00000000402b5328";
SCOPE = "service::user.auth.xboxlive.com::MBI_SSL"
REDIRECT_URI = "https://login.live.com/oauth20_desktop.srf"

LOGIN_URL = "https://login.live.com/oauth20_authorize.srf?"+urllib.parse.urlencode({
    'client_id' : CLIENT_ID,
    'response_type':'code',
    'scope': SCOPE,
    'redirect_uri' : REDIRECT_URI
})
AUTH_TOKEN_URL = "https://login.live.com/oauth20_token.srf"
XBL_TOKEN_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_TOKEN_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_TOKEN_URL =  "https://api.minecraftservices.com/authentication/login_with_xbox"
PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"

# Expected data:
#   sFTTag: '<input type="hidden" name="PPFT"
#   id="12345" value="random stuff"/>'
#
# This is all inside a long <script> tag on the LOGIN_URL webpage.

PPFT_REGEX = "sFTTag:[ ]?'.*value=\"(.*)\"/>"

# Expected data: 
#   urlPost: 'https://login.live.com/...'
# This appears earlier in the same <script> tag.

URLPOST_REGEX = "urlPost:[ ]?'(.+?(?='))"
AUTHCODE_REGEX = "[?|&]code=([\\w.-]+)"


def getAuthorizationCode(email,password):
    r = requests.get(LOGIN_URL)
    cookies = r.cookies
    content = r.text
    ppft = re.search(PPFT_REGEX,content).group(1)
    urlPost = re.search(URLPOST_REGEX,content).group(1)

    return microsoftLogin(email,password,cookies,urlPost,ppft)

def microsoftLogin(email,password,cookies,urlPost,ppft):
    data = {
        'login':email,
        'loginfmt':email,
        'passwd':password,
        'PPFT':ppft
    }


    r = requests.post(urlPost,cookies=cookies,data=data)

    code = re.search(AUTHCODE_REGEX,r.url).group(1)
    return code

def getMicrosoftAccessToken(authCode):
    data = {
        "client_id": CLIENT_ID,
        "code": authCode,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    }

    r = requests.post(AUTH_TOKEN_URL,data=data)
    j = json.loads(r.text)
    return j['access_token']

def getXBLToken(msftAccessToken):
    data = {
        "RelyingParty": "https://auth.xboxlive.com",
        "TokenType": "JWT",
        "properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": msftAccessToken,
        }
    }
    r = requests.post(XBL_TOKEN_URL,json=data)
    j = json.loads(r.text)
    return j['Token'],j['DisplayClaims']['xui'][0]['uhs']

def getXSTSToken(xblToken):
    data = {
        'RelyingParty':  'rp://api.minecraftservices.com/',
        'TokenType': 'JWT',
        'Properties': {
            'SandboxId': 'RETAIL',
            'UserTokens': [
                xblToken
            ]
        }
    }

    r = requests.post(XSTS_TOKEN_URL,json=data)
    return json.loads(r.text)['Token']

def getMinecraftAccessToken(UHSToken, xstsToken):
    data = {
        'identityToken': ('XBL3.0 x=' + UHSToken + ';' + xstsToken)
    }
    r = requests.post(MC_TOKEN_URL,json=data)
    return json.loads(r.text)['access_token']

def getMinecraftProfile(mcAccessToken):
    headers = {
        'Authorization' : 'Bearer ' + mcAccessToken
    }
    r = requests.get(PROFILE_URL,headers=headers)
    return json.loads(r.text)

def login(email,password):
    authCode = getAuthorizationCode(email,password)
    msftAccessToken = getMicrosoftAccessToken(authCode)
    XBLToken, UHSToken = getXBLToken(msftAccessToken)
    xstsToken = getXSTSToken(XBLToken)
    mcAccessToken = getMinecraftAccessToken(UHSToken,xstsToken)
    profile = getMinecraftProfile(mcAccessToken)
    return mcAccessToken, profile['name'], profile['id']