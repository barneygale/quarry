import base64

from twisted.internet import reactor, defer

from quarry.net.protocol import Factory, Protocol, ProtocolError, \
    protocol_modes, register
from quarry.mojang import auth
from quarry.util import crypto, types


class ServerProtocol(Protocol):
    """This class represents a connection with a client"""

    uuid = None
    username = None
    username_confirmed = False

    # used to stop people breaking the login process
    # by sending packets out-of-order or duplicated
    login_expecting = 0

    # the mojang 1.7.x client has a race condition where kicking immediately
    # after switching to "play" mode will cause a cast error in the client.
    # the fix is to set a deferred up which will fire when it's safe again
    safe_kick = None

    def __init__(self, factory, addr):
        Protocol.__init__(self, factory, addr)
        self.server_id    = crypto.make_server_id()
        self.verify_token = crypto.make_verify_token()


    ### Convenience functions -------------------------------------------------

    def switch_protocol_mode(self, mode):
        self.check_protocol_mode_switch(mode)

        if mode == "play":
            # Send login success
            self.send_packet(2,
                self.buff_type.pack_string(self.uuid.to_hex()) +
                self.buff_type.pack_string(self.username))

            if self.protocol_version <= 5:
                def make_safe():
                    self.safe_kick.callback(None)
                    self.safe_kick = None

                def make_unsafe():
                    self.safe_kick = defer.Deferred()
                    self.tasks.add_delay(0.5, make_safe)

                make_unsafe()

        self.protocol_mode = mode

    def close(self, reason=None):
        if not self.closed and reason is not None:
            # Kick the player if possible.
            if self.protocol_mode == "play":
                def real_kick(*a):
                    self.send_packet(0x40, self.buff_type.pack_chat(reason))
                    Protocol.close(self, reason)

                if self.safe_kick:
                    self.safe_kick.addCallback(real_kick)
                else:
                    real_kick()
            else:
                if self.protocol_mode == "login":
                    self.send_packet(0x00, self.buff_type.pack_chat(reason))
                Protocol.close(self, reason)
        else:
            Protocol.close(self, reason)

    ### Callbacks -------------------------------------------------------------

    def auth_ok(self, data):
        self.username_confirmed = True
        self.uuid = types.UUID.from_hex(data['id'])

        self.player_joined()

    def player_joined(self):
        Protocol.player_joined(self)

        self.logger.info("%s has joined." % self.username)

        self.switch_protocol_mode("play")

    def player_left(self):
        Protocol.player_left(self)

        self.logger.info("%s has left." % self.username)

    ### Packet handlers -------------------------------------------------------

    @register("init", 0x00)
    def packet_handshake(self, buff):
        p_protocol_version = buff.unpack_varint()
        p_server_addr = buff.unpack_string()
        p_server_port = buff.unpack("H")
        p_protocol_mode = buff.unpack_varint()

        mode = protocol_modes.get(p_protocol_mode, p_protocol_mode)
        self.switch_protocol_mode(mode)

        if mode == "login" \
                and p_protocol_version not in self.factory.protocol_versions:

            self.close("Wrong protocol version")

        self.protocol_version = p_protocol_version

    @register("login", 0x00)
    def packet_login_start(self, buff):
        if self.login_expecting != 0:
            raise ProtocolError("Out-of-order login")

        self.username = buff.unpack_string()

        if self.factory.online_mode:
            self.login_expecting = 1

            # send encryption request

            # 1.7.x
            if self.protocol_version <= 5:
                self.send_packet(1,
                    self.buff_type.pack_string(self.server_id) +
                    self.buff_type.pack('H', len(self.factory.public_key)) +
                    self.buff_type.pack_raw(self.factory.public_key) +
                    self.buff_type.pack('H', len(self.verify_token)) +
                    self.buff_type.pack_raw(self.verify_token))

            # 1.8.x
            else:
                self.send_packet(1,
                    self.buff_type.pack_string(self.server_id) +
                    self.buff_type.pack_varint(len(self.factory.public_key)) +
                    self.buff_type.pack_raw(self.factory.public_key) +
                    self.buff_type.pack_varint(len(self.verify_token)) +
                    self.buff_type.pack_raw(self.verify_token))

        else:
            self.login_expecting = None
            self.username_confirmed = True
            self.uuid = types.UUID.from_offline_player(self.username)

            self.player_joined()

    @register("login", 0x01)
    def packet_encryption_response(self, buff):
        if self.login_expecting != 1:
            raise ProtocolError("Out-of-order login")

        # 1.7.x
        if self.protocol_version <= 5:
            p_shared_secret = buff.unpack_raw(buff.unpack('h'))
            p_verify_token = buff.unpack_raw(buff.unpack('h'))

        # 1.8.x
        else:
            p_shared_secret = buff.unpack_raw(buff.unpack_varint())
            p_verify_token = buff.unpack_raw(buff.unpack_varint())

        shared_secret = crypto.decrypt_secret(
            self.factory.keypair,
            p_shared_secret)

        verify_token = crypto.decrypt_secret(
            self.factory.keypair,
            p_verify_token
        )

        self.login_expecting = None

        if verify_token != self.verify_token:
            raise ProtocolError("Verify token incorrect")

        # enable encryption
        self.cipher.enable(shared_secret)
        self.logger.debug("Encryption enabled")

        # make digest
        digest = crypto.make_digest(
            self.server_id,
            shared_secret,
            self.factory.public_key)

        # do auth
        deferred = auth.has_joined(
            self.factory.auth_timeout,
            digest,
            self.username)
        deferred.addCallbacks(self.auth_ok, self.auth_failed)

    @register("status", 0x00)
    def packet_status_request(self, buff):
        d = {
            "description": {
                "text":     self.factory.motd
            },
            "players": {
                "online":   len(self.factory.players),
                "max":      self.factory.max_players
            },
            "version": {
                "name":     self.factory.protocol_versions.get(
                                self.protocol_version,
                                "???"),
                "protocol": self.protocol_version
            }
        }
        if self.factory.favicon:
            d["favicon"] = self.factory.favicon

        # send status response
        self.send_packet(0, self.buff_type.pack_json(d))

    @register("status", 0x01)
    def packet_status_ping(self, buff):
        time = buff.unpack("Q")

        # send ping
        self.send_packet(1, self.buff_type.pack("Q", time))
        self.close()


class ServerFactory(Factory):
    protocol = ServerProtocol

    motd = "A Minecraft Server"
    max_players = 20
    favicon = None
    favicon_path = None
    online_mode = True

    def __init__(self):
        self.players = []

        self.keypair = crypto.make_keypair()
        self.public_key = crypto.export_public_key(self.keypair)

        if self.favicon_path is not None:
            favicon_data = open(self.favicon_path).read()
            favicon_data = base64.encodestring(favicon_data)
            self.favicon = "data:image/png;base64," + favicon_data

    def listen(self, addr, port=25565):
        reactor.listenTCP(port, self, interface=addr)