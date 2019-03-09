import base64
from twisted.internet import reactor, defer
from cached_property import cached_property

from quarry.net.protocol import Factory, Protocol, ProtocolError, \
    protocol_modes
from quarry.net import auth, crypto
from quarry.types.uuid import UUID


class ServerProtocol(Protocol):
    """This class represents a connection with a client"""

    recv_direction = "upstream"
    send_direction = "downstream"

    uuid = None
    display_name = None
    display_name_confirmed = False

    # the hostname/port that the client claims it connected to. Useful for
    # implementing virtual hosting.
    connect_host = None
    connect_port = None

    # used to stop people breaking the login process
    # by sending packets out-of-order or duplicated
    login_expecting = 0

    # the mojang 1.7.x client has a race condition where kicking immediately
    # after switching to "play" mode will cause a cast error in the client.
    # the fix is to set a deferred up which will fire when it's safe again
    safe_kick = None

    def __init__(self, factory, remote_addr):
        Protocol.__init__(self, factory, remote_addr)
        self.server_id = crypto.make_server_id()
        self.verify_token = crypto.make_verify_token()

    # Convenience functions ---------------------------------------------------

    def switch_protocol_mode(self, mode):
        self.check_protocol_mode_switch(mode)

        if mode == "play":
            if self.factory.compression_threshold:
                # Send set compression
                self.send_packet(
                    "login_set_compression",
                    self.buff_type.pack_varint(
                        self.factory.compression_threshold))
                self.set_compression(self.factory.compression_threshold)

            # Send login success
            self.send_packet(
                "login_success",
                self.buff_type.pack_string(self.uuid.to_hex()) +
                self.buff_type.pack_string(self.display_name))

            if self.protocol_version <= 5:
                def make_safe():
                    self.safe_kick.callback(None)
                    self.safe_kick = None

                def make_unsafe():
                    self.safe_kick = defer.Deferred()
                    self.ticker.add_delay(10, make_safe)

                make_unsafe()

        self.protocol_mode = mode

    def close(self, reason=None):
        """Closes the connection"""
        if not self.closed and reason is not None:
            # Kick the player if possible.
            if self.protocol_mode == "play":
                def real_kick(*a):
                    self.send_packet(
                        "disconnect",
                        self.buff_type.pack_chat(reason))
                    super(ServerProtocol, self).close(reason)

                if self.safe_kick:
                    self.safe_kick.addCallback(real_kick)
                else:
                    real_kick()
            else:
                if self.protocol_mode == "login":
                    self.send_packet(
                        "login_disconnect",
                        self.buff_type.pack_chat(reason))
                Protocol.close(self, reason)
        else:
            Protocol.close(self, reason)

    # Callbacks ---------------------------------------------------------------

    def connection_lost(self, reason=None):
        """Called when the connection is lost"""
        if self.protocol_mode in ("login", "play"):
            self.factory.players.discard(self)
        Protocol.connection_lost(self, reason)

    def auth_ok(self, data):
        """Called when auth with mojang succeeded (online mode only)"""
        self.display_name_confirmed = True
        self.uuid = UUID.from_hex(data['id'])

        self.player_joined()

    def player_joined(self):
        """Called when the player joins the game"""
        Protocol.player_joined(self)

        self.logger.info("%s has joined." % self.display_name)

        self.switch_protocol_mode("play")

    def player_left(self):
        """Called when the player leaves the game"""
        Protocol.player_left(self)

        self.logger.info("%s has left." % self.display_name)

    # Packet handlers ---------------------------------------------------------

    def packet_handshake(self, buff):
        p_protocol_version = buff.unpack_varint()
        p_connect_host = buff.unpack_string()
        p_connect_port = buff.unpack("H")
        p_protocol_mode = buff.unpack_varint()

        mode = protocol_modes.get(p_protocol_mode, p_protocol_mode)
        self.switch_protocol_mode(mode)

        if mode == "login":
            if self.factory.force_protocol_version is not None:
                if p_protocol_version != self.factory.force_protocol_version:
                    self.close("Wrong protocol version")
            else:
                if p_protocol_version not in self.factory.minecraft_versions:
                    self.close("Unknown protocol version")

            if len(self.factory.players) >= self.factory.max_players:
                self.close("Server is full")
            else:
                self.factory.players.add(self)

        self.protocol_version = p_protocol_version
        self.buff_type = self.factory.get_buff_type(self.protocol_version)
        self.connect_host = p_connect_host
        self.connect_port = p_connect_port

    def packet_login_start(self, buff):
        if self.login_expecting != 0:
            raise ProtocolError("Out-of-order login")

        self.display_name = buff.unpack_string()

        if self.factory.online_mode:
            self.login_expecting = 1

            # send encryption request

            # 1.7.x
            if self.protocol_version <= 5:
                pack_array = lambda a: self.buff_type.pack('h', len(a)) + a

            # 1.8.x
            else:
                pack_array = lambda a: self.buff_type.pack_varint(
                    len(a), max_bits=16) + a

            self.send_packet(
                "login_encryption_request",
                self.buff_type.pack_string(self.server_id),
                pack_array(self.factory.public_key),
                pack_array(self.verify_token))

        else:
            self.login_expecting = None
            self.display_name_confirmed = True
            self.uuid = UUID.from_offline_player(self.display_name)

            self.player_joined()

    def packet_login_encryption_response(self, buff):
        if self.login_expecting != 1:
            raise ProtocolError("Out-of-order login")

        # 1.7.x
        if self.protocol_version <= 5:
            unpack_array = lambda b: b.read(b.unpack('h'))
        # 1.8.x
        else:
            unpack_array = lambda b: b.read(b.unpack_varint(max_bits=16))

        p_shared_secret = unpack_array(buff)
        p_verify_token = unpack_array(buff)

        shared_secret = crypto.decrypt_secret(
            self.factory.keypair,
            p_shared_secret)

        verify_token = crypto.decrypt_secret(
            self.factory.keypair,
            p_verify_token)

        self.login_expecting = None

        if verify_token != self.verify_token:
            raise ProtocolError("Verify token incorrect")

        # enable encryption
        self.cipher.enable(shared_secret)
        self.logger.debug("Encryption enabled")

        # make digest
        digest = crypto.make_digest(
            self.server_id.encode('ascii'),
            shared_secret,
            self.factory.public_key)

        # do auth
        remote_host = None
        if self.factory.prevent_proxy_connections:
            remote_host = self.remote_addr.host
        deferred = auth.has_joined(
            self.factory.auth_timeout,
            digest,
            self.display_name,
            remote_host)
        deferred.addCallbacks(self.auth_ok, self.auth_failed)

    def packet_status_request(self, buff):
        protocol_version = self.factory.force_protocol_version
        if protocol_version is None:
            protocol_version = self.protocol_version

        d = {
            "description": {
                "text":     self.factory.motd
            },
            "players": {
                "online":   len(self.factory.players),
                "max":      self.factory.max_players
            },
            "version": {
                "name":     self.factory.minecraft_versions.get(
                                protocol_version,
                                "???"),
                "protocol": protocol_version
            }
        }
        if self.factory.icon is not None:
            d['favicon'] = self.factory.icon

        # send status response
        self.send_packet("status_response", self.buff_type.pack_json(d))

    def packet_status_ping(self, buff):
        time = buff.unpack("Q")

        # send ping
        self.send_packet("status_pong", self.buff_type.pack("Q", time))
        self.close()


class ServerFactory(Factory):
    protocol = ServerProtocol

    motd = "A Minecraft Server"
    max_players = 20
    icon_path = None
    online_mode = True
    prevent_proxy_connections = True
    compression_threshold = 256
    auth_timeout = 30
    players = None

    def __init__(self):
        self.players = set()

        self.keypair = crypto.make_keypair()
        self.public_key = crypto.export_public_key(self.keypair)

    def listen(self, host, port=25565):
        reactor.listenTCP(port, self, interface=host)

    @cached_property
    def icon(self):
        if self.icon_path is not None:
            with open(self.icon_path, "rb") as fd:
                return "data:image/png;base64," + base64.encodebytes(
                    fd.read()).decode('ascii').replace('\n', '')
