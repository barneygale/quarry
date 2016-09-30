from twisted.internet import defer

from quarry.utils import http, types


class ProfileException(http.HTTPException):
    pass


class Profile(object):
    timeout = 30
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

    def _req(self, endpoint, **data):
        return http.request(
            url=b"https://authserver.mojang.com/"+endpoint,
            timeout=self.timeout,
            err_type=ProfileException,
            data=data)

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

        clientToken = "foo" #TODO

        d1 = self._req(b"authenticate",
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

        d1 = self._req(b"refresh",
            clientToken = client_token,
            accessToken = access_token,
            selectedProfile = {
                "name": username,
                "id": uuid.to_hex()
            }
        )
        d1.addCallbacks(_callback, _errback)

        return d0

    def invalidate(self):
        return self._req(b"invalidate",
            clientToken = self.client_token,
            accessToken = self.access_token,
        )

    #TODO: validate
    #TODO: sign out