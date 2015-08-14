import json

from twisted.internet import defer
from twisted.web import client, error
from twisted.python import failure

client.HTTPClientFactory.noisy = False


class AuthException(Exception):
    pass


def join(timeout, digest, access_token, uuid):
    d0 = defer.Deferred()

    def _auth_ok(data):
        d0.callback(json.loads(data.decode('ascii')))

    def _auth_err(err):
        if isinstance(err.value, error.Error) and err.value.status == b"204":
            d0.callback(None)
        else:
            d0.errback(err)

    data = {
        "accessToken": access_token,
        "selectedProfile": uuid.to_hex(with_dashes=False),
        "serverId": digest
    }

    d1 = client.getPage(
        b"https://sessionserver.mojang.com/session/minecraft/join",
        headers = {b'Content-Type': b'application/json'},
        method = b'POST',
        postdata = json.dumps(data).encode('ascii'),
        timeout = timeout)
    d1.addCallbacks(_auth_ok, _auth_err)

    return d0


def has_joined(timeout, digest, username):
    d0 = defer.Deferred()

    def _auth_ok(data):
        d0.callback(json.loads(data.decode('ascii')))

    def _auth_err(err):
        if isinstance(err.value, error.Error) and err.value.status == b"204":
            err = failure.Failure(AuthException("Failed to verify user"))
        d0.errback(err)

    d1 = client.getPage(
        b"https://sessionserver.mojang.com/session/minecraft/hasJoined"
        b"?username=" + username.encode('ascii') + \
        b"&serverId=" + digest.encode('ascii'),
        timeout = timeout)
    d1.addCallbacks(_auth_ok, _auth_err)

    return d0