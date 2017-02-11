from twisted.internet import reactor, protocol, defer
from twisted.python import failure

from quarry.net.protocol import Factory, Protocol, protocol_modes_inv
from quarry import auth
from quarry.utils import crypto
from quarry.utils.errors import ProtocolError


class ClientProtocol(Protocol):
    """This class represents a connection to a server"""

    recv_direction = "downstream"
    send_direction = "upstream"
    protocol_mode_next = None

    def __init__(self, factory, remote_addr):
        Protocol.__init__(self, factory, remote_addr)

    ### Convenience functions -------------------------------------------------

    def switch_protocol_mode(self, mode):
        self.check_protocol_mode_switch(mode)

        if mode in ("status", "login"):
            # Send handshake
            addr = self.transport.connector.getDestination()
            self.send_packet("handshake",
                self.buff_type.pack_varint(self.protocol_version) +
                self.buff_type.pack_string(addr.host) +
                self.buff_type.pack('H', addr.port) +
                self.buff_type.pack_varint(
                    protocol_modes_inv[self.protocol_mode_next]))

        self.protocol_mode = mode

        if mode == "status":
            # Send status request
            self.send_packet("status_request")

        elif mode == "login":
            # Send login start
            self.send_packet("login_start", self.buff_type.pack_string(
                self.factory.profile.display_name))


    ### Callbacks -------------------------------------------------------------

    def connection_made(self):
        """Called when the connection is established"""
        Protocol.connection_made(self)
        self.switch_protocol_mode(self.protocol_mode_next)

    def auth_ok(self, data):
        """
        Called if the Mojang session server responds to our query. Note that
        this method does not indicate that the server accepted our session; in
        this case :meth:`player_joined` is called.
        """

        # Send encryption response
        p_shared_secret = crypto.encrypt_secret(
            self.public_key,
            self.shared_secret)
        p_verify_token = crypto.encrypt_secret(
            self.public_key,
            self.verify_token)

        # 1.7.x
        if self.protocol_version <= 5:
            pack_array = lambda d: self.buff_type.pack('h', len(d)) + d

        # 1.8.x
        else:
            pack_array = lambda d: self.buff_type.pack_varint(
                len(d), max_bits=16) + d

        self.send_packet("login_encryption_response",
            pack_array(p_shared_secret) +
            pack_array(p_verify_token))

        # Enable encryption
        self.cipher.enable(self.shared_secret)
        self.logger.debug("Encryption enabled")

    def player_joined(self):
        """
        Called when we join the game. If the server is in online mode, this
        means the server accepted our session.
        """
        Protocol.player_joined(self)
        self.logger.info("Joined the game.")

    def player_left(self):
        """Called when we leave the game."""
        Protocol.player_left(self)
        self.logger.info("Left the game.")

    def status_response(self, data):
        """
        If we're connecting in "status" mode, this is called when the server
        sends us information about itself.
        """
        self.close()

    ### Packet handlers -------------------------------------------------------

    def packet_status_response(self, buff):
        p_data = buff.unpack_json()
        self.status_response(p_data)

    def packet_login_disconnect(self, buff):
        p_data = buff.unpack_chat()
        self.logger.warn("Kicked: %s" % p_data)
        self.close()

    def packet_login_encryption_request(self, buff):
        p_server_id    = buff.unpack_string()

        # 1.7.x
        if self.protocol_version <= 5:
            unpack_array = lambda b: b.read(b.unpack('h'))
        # 1.8.x
        else:
            unpack_array = lambda b: b.read(b.unpack_varint(max_bits=16))

        p_public_key   = unpack_array(buff)
        p_verify_token = unpack_array(buff)

        if not self.factory.profile.online:
            raise ProtocolError("Can't log into online-mode server while using"
                                " offline profile")

        self.shared_secret = crypto.make_shared_secret()
        self.public_key = crypto.import_public_key(p_public_key)
        self.verify_token  = p_verify_token

        # make digest
        digest = crypto.make_digest(
            p_server_id.encode('ascii'),
            self.shared_secret,
            p_public_key)

        # do auth
        deferred = self.factory.profile.join(digest)
        deferred.addCallbacks(self.auth_ok, self.auth_failed)

    def packet_login_success(self, buff):
        p_uuid = buff.unpack_string()
        p_display_name = buff.unpack_string()

        self.switch_protocol_mode("play")
        self.player_joined()

    def packet_login_set_compression(self, buff):
        self.set_compression(buff.unpack_varint())

    def packet_set_compression(self, buff):
        self.set_compression(buff.unpack_varint())

    packet_disconnect = packet_login_disconnect


class SpawningClientProtocol(ClientProtocol):
    spawned = False

    def __init__(self, factory, remote_addr):
        # x, y, z, yaw, pitch
        self.pos_look = [0, 0, 0, 0, 0]

        super(SpawningClientProtocol, self).__init__(factory, remote_addr)

    # Send a 'player' packet every tick
    def update_player_inc(self):
        self.send_packet("player", self.buff_type.pack('?', True))

    # Sent a 'player position' packet every 20 ticks
    def update_player_full(self):
        self.send_packet("player_position", self.buff_type.pack('ddd?',
            self.pos_look[0],
            self.pos_look[1],
            self.pos_look[2],
            True))

    def packet_player_position_and_look(self, buff):
        p_pos_look = buff.unpack('dddff')

        # 1.7.x
        if self.protocol_version <= 5:
            p_on_ground = buff.unpack('?')
            self.pos_look = p_pos_look

        # 1.8.x
        else:
            p_flags = buff.unpack('B')

            for i in range(5):
                if p_flags & (1 << i):
                    self.pos_look[i] += p_pos_look[i]
                else:
                    self.pos_look[i] = p_pos_look[i]

            # 1.9.x
            if self.protocol_version > 47:
                teleport_id = buff.unpack_varint()

        # Send Player Position And Look

        # 1.7.x
        if self.protocol_version <= 5:
            self.send_packet("player_position_and_look", self.buff_type.pack(
                'ddddff?',
                self.pos_look[0],
                self.pos_look[1] - 1.62,
                self.pos_look[1],
                self.pos_look[2],
                self.pos_look[3],
                self.pos_look[4],
                True))

        # 1.8.x
        elif self.protocol_version <= 47:
            self.send_packet("player_position_and_look", self.buff_type.pack(
                'dddff?',
                self.pos_look[0],
                self.pos_look[1],
                self.pos_look[2],
                self.pos_look[3],
                self.pos_look[4],
                True))

        # 1.9.x
        else:
            self.send_packet("teleport_confirm", self.buff_type.pack_varint(
                teleport_id))

        if not self.spawned:
            self.tasks.add_loop(1.0/20, self.update_player_inc)
            self.tasks.add_loop(1.0,    self.update_player_full)
            self.spawned = True


class ClientFactory(Factory, protocol.ClientFactory):
    protocol = ClientProtocol

    def __init__(self, profile=None):
        if profile is None:
            profile = auth.OfflineProfile()
        self.profile = profile

    def connect(self, host, port=25565, protocol_mode_next="login",
                protocol_version=0):

        if protocol_mode_next == "status" or protocol_version > 0:
            self.protocol.protocol_mode_next = protocol_mode_next
            if protocol_version > 0:
                self.protocol.protocol_version = protocol_version
            reactor.connectTCP(host, port, self, self.connection_timeout)
            return defer.succeed(self)
        else:
            d0 = defer.Deferred()
            factory = ClientFactory()
            class PingProtocol(factory.protocol):
                def status_response(s, data):
                    s.close()
                    detected_version = int(data["version"]["protocol"])
                    if detected_version in self.minecraft_versions:
                        d1 = self.connect(host, port, protocol_mode_next,
                                     detected_version)
                        d1.chainDeferred(d0)
                    else:
                        d0.errback(failure.Failure(ProtocolError(
                            "Unsupported protocol version: %d"
                            % detected_version)))

            factory.protocol = PingProtocol
            factory.connect(host, port, "status")
            return d0
