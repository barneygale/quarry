import argparse
import json
import os
import sys

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from twisted.internet import defer
from quarry.net import http
from quarry.types.uuid import UUID

if sys.version_info[0] == 2:
    from urllib import urlencode
else:
    from urllib.parse import urlencode

SESSION_SERVER = b"https://sessionserver.mojang.com/session/minecraft/"


class ProfileException(http.HTTPException):
    pass


class AuthException(http.HTTPException):
    pass


class OfflineProfile(object):
    online = False

    def __init__(self, display_name="quarry", uuid="00000000-0000-0000-0000-000000000000"):
        self.display_name = display_name
        self.uuid = uuid

    @classmethod
    def from_display_name(cls, display_name):
        return cls(display_name)
    
    @classmethod
    def from_uuid(cls, uuid):
        return cls(uuid)


class Profile(object):
    online = True
    timeout = 30

    def __init__(self, client_token, access_token, display_name, uuid):
        self.client_token = client_token
        self.access_token = access_token
        self.display_name = display_name
        self.uuid = uuid

    def join(self, digest, refresh=True):
        d1 = http.request(
            url=SESSION_SERVER + b"join",
            timeout=self.timeout,
            err_type=AuthException,
            data={"accessToken": self.access_token,
                  "selectedProfile": self.uuid.to_hex(with_dashes=False),
                  "serverId": digest})

        if not refresh:
            return d1
        else:
            d0 = defer.Deferred()

            def _errback(err):
                self.refresh().chainDeferred(
                    self.join(digest, refresh=False).chainDeferred(d0))
            d1.addCallbacks(d0.callback, _errback)
            return d0

    def validate(self):
        d0 = defer.Deferred()

        def _callback(data):
            d0.callback(self)

        d1 = self._request(b"validate", accessToken=self.access_token)
        d1.addCallbacks(_callback, d0.errback)
        return d0

    def refresh(self):
        d0 = defer.Deferred()

        def _callback(data):
            d0.callback(self)

        d1 = self._request(
            b"refresh",
            clientToken=self.client_token,
            accessToken=self.access_token)
        d1.addCallbacks(_callback, d0.errback)
        return d0

    def to_file(self, profiles_path=None):
        if not profiles_path:
            profiles_path = self._get_profiles_path()

        with open(profiles_path, "w") as fd:
            json.dump({
                "selectedUser": self.uuid.to_hex(False),
                "clientToken": self.client_token,
                "authenticationDatabase": {
                    self.uuid.to_hex(False): {
                        "displayName": self.display_name,
                        "accessToken": self.access_token,
                        "uuid": self.uuid.to_hex(True)}}}, fd)

    @classmethod
    def from_credentials(cls, email, password):
        d0 = defer.Deferred()

        def _callback(data):
            d0.callback(cls._from_response(data))

        def _errback(err):
            d0.errback(err)

        agent = {
            "name": "Minecraft",
            "version": 1
        }

        client_token = "foo"  # TODO

        d1 = cls._request(
            b"authenticate",
            username=email,
            password=password,
            agent=agent,
            clientToken=client_token)
        d1.addCallbacks(_callback, _errback)

        return d0

    @classmethod
    def from_token(cls, client_token, access_token, display_name, uuid):
        obj = cls(client_token, access_token,
                  display_name, UUID.from_hex(uuid))
        return obj.validate()

    @classmethod
    def from_file(cls, display_name=None, uuid=None, profiles_path=None):
        if profiles_path is None:
            profiles_path = cls._get_profiles_path()

        with open(profiles_path) as fd:
            data = json.load(fd)

        client_token = data["clientToken"]

        if display_name is None and uuid is None:
            uuid = data["selectedUser"]["profile"]

        for store in data["authenticationDatabase"].values():
            access_token = store["accessToken"]

            for p_uuid, p_data in store["profiles"].items():
                p_display_name = p_data["displayName"]
                if uuid and uuid != p_uuid:
                    continue
                if display_name and display_name != p_display_name:
                    continue
                return cls.from_token(client_token, access_token,
                                      p_display_name, p_uuid)

    @classmethod
    def _from_response(cls, response):
        return cls(
            response['clientToken'],
            response['accessToken'],
            response['selectedProfile']['name'],
            UUID.from_hex(response['selectedProfile']['id']))

    @classmethod
    def _request(cls, endpoint, **data):
        return http.request(
            url=b"https://authserver.mojang.com/" + endpoint,
            timeout=cls.timeout,
            err_type=ProfileException,
            data=data)

    @classmethod
    def _get_profiles_path(cls):
        dot_minecraft = ".minecraft"
        if sys.platform == 'win32':
            app_data = os.environ['APPDATA']
        elif sys.platform == 'darwin':
            app_data = os.path.expanduser("~/Library/Application Support")
            dot_minecraft = "minecraft"
        else:
            app_data = os.path.expanduser("~")
        return os.path.join(
            app_data, dot_minecraft, "launcher_profiles.json")


class ProfileCLI(object):
    @classmethod
    def make_parser(cls, parser=None):
        if parser is None:
            parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--auth",
            metavar="EMAIL:PASSWORD",
            help="Sets the Mojang account email address and password with "
                 "which to log in.")
        group.add_argument(
            "--session-name",
            metavar="DISPLAY_NAME",
            help="Sets the display name to look up in the "
                 "~/.minecraft/launcher_profiles.json file. This is used to "
                 "resume an existing logged-in session from the official "
                 "client.")
        group.add_argument(
            "--offline-name",
            metavar="DISPLAY_NAME",
            help="Sets the offline display name to use. If none of these "
                 "options are given, quarry uses 'quarry' as an offline "
                 "display name.")
        return parser

    @classmethod
    def make_profile(cls, args):
        if args.auth:
            email, password = args.auth.split(":", 1)
            return Profile.from_credentials(email, password)
        if args.session_name:
            return Profile.from_file(args.session_name)
        return defer.succeed(
            OfflineProfile.from_display_name(args.offline_name or "quarry"))


class PlayerPublicKey:
    def __init__(self, expiry: int, key: RSAPublicKey, signature: bytes):
        self.key = key
        self.signature = signature
        self.expiry = expiry


def has_joined(timeout, digest, display_name, remote_host=None):
    data = {"username": display_name, "serverId": digest}
    if remote_host:
        data["ip"] = remote_host

    return http.request(
        url=SESSION_SERVER + b"hasJoined?" + urlencode(data).encode('ascii'),
        timeout=timeout,
        err_type=AuthException,
        expect_content=True)
