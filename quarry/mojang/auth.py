from quarry.utils import http


class AuthException(http.HTTPException):
    pass


def join(timeout, digest, access_token, uuid):
    return http.request(
        url=b"https://sessionserver.mojang.com/session/minecraft/join",
        timeout=timeout,
        err_type=AuthException,
        data={
            "accessToken": access_token,
            "selectedProfile": uuid.to_hex(with_dashes=False),
            "serverId": digest})

def has_joined(timeout, digest, username):
    return http.request(
        url=b"https://sessionserver.mojang.com/session/minecraft/hasJoined"
            b"?username=" + username.encode('ascii') + \
            b"&serverId=" + digest.encode('ascii'),
        timeout=timeout,
        err_type=AuthException,
        expect_content=True)