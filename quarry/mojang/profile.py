import json

from twisted.internet import defer
from twisted.web import client, error
from twisted.python import failure

from quarry.util import types

client.HTTPClientFactory.noisy = False


class YggdasilException(Exception):
    def __init__(self, error_type, error_message):
        self.error_type = error_type
        self.error_message = error_message

    def __str__(self):
        return "%s: %s" % (self.error_type, self.error_message)


class YggdasilType(type):
    def __getattr__(cls, endpoint):
        def _attr(**data):
            d0 = defer.Deferred()

            def _callback(data):
                d0.callback(json.loads(data))

            def _errback(err):
                if isinstance(err.value, error.Error):
                    data = json.loads(err.value.response)
                    err = failure.Failure(YggdasilException(
                        data['error'],
                        data['errorMessage']))
                d0.errback(err)

            d1 = client.getPage(
                "https://authserver.mojang.com/"+endpoint,
                headers = {'Content-Type': 'application/json'},
                method = 'POST',
                postdata = json.dumps(data))

            d1.addCallbacks(_callback, _errback)

            return d0
        return _attr


class Yggdasil:
    __metaclass__ = YggdasilType


class Profile:
    client_token = None
    access_token = None
    username = None
    uuid = None

    logged_in = False

    def _setData(self, data):
        self.client_token = data['clientToken']
        self.access_token = data['accessToken']
        self.username = data['selectedProfile']['name']
        self.uuid = types.UUID.from_hex(data['selectedProfile']['id'])

    def login_offline(self, username):
        self.username = username

    def login(self, username, password):
        d0 = defer.Deferred()

        def _callback(data):
            self._setData(data)
            self.logged_in = True
            d0.callback(data)

        def _errback(err):
            d0.errback(err)

        agent = {
            "name": "Minecraft",
            "version": 1
        }

        clientToken = None #TODO

        d1 = Yggdasil.authenticate(
            username = username,
            password = password,
            agent = agent,
            clientToken = clientToken
        )
        d1.addCallbacks(_callback, _errback)

        return d0

    def refresh(self, client_token, access_token, username, uuid):
        d0 = defer.Deferred()

        def _callback(data):
            self._setData(data)
            self.logged_in = True
            d0.callback(data)

        def _errback(err):
            d0.errback(err)

        d1 = Yggdasil.refresh(
            clientToken = client_token,
            accessToken = access_token,
            selectedProfile = {
                "name": username,
                "id": uuid.to_hex()
            }
        )
        d1.addCallbacks(_callback, _errback)

        return d0

    #TODO: validate
    #TODO: invalidate
    #TODO: sign out