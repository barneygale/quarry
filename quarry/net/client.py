from twisted.internet import reactor, protocol, defer

from quarry.net.protocol import Factory, Protocol, protocol_modes_inv
from quarry.mojang import auth
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
                self.factory.profile.username))


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

        if not self.factory.profile.logged_in:
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
        deferred = auth.join(
            self.factory.auth_timeout,
            digest,
            self.factory.profile.access_token,
            self.factory.profile.uuid)
        deferred.addCallbacks(self.auth_ok, self.auth_failed)

    def packet_login_success(self, buff):
        p_uuid = buff.unpack_string()
        p_username = buff.unpack_string()

        self.switch_protocol_mode("play")
        self.player_joined()

    def packet_login_set_compression(self, buff):
        self.set_compression(buff.unpack_varint())

    def packet_set_compression(self, buff):
        self.set_compression(buff.unpack_varint())

class ClientFactory(Factory, protocol.ClientFactory):
    protocol = ClientProtocol
    profile = None

    def connect(self, host, port=25565, protocol_mode_next="login",
                protocol_version=0):

        if protocol_mode_next == "status" or protocol_version > 0:
            self.protocol.protocol_mode_next = protocol_mode_next
            if protocol_version > 0:
                self.protocol.protocol_version = protocol_version
            reactor.connectTCP(host, port, self, self.connection_timeout)

        else:
            factory = ClientFactory()
            class PingProtocol(factory.protocol):
                def status_response(s, data):
                    s.close()
                    detected_version = int(data["version"]["protocol"])
                    if detected_version in self.minecraft_versions:
                        self.connect(host, port, protocol_mode_next,
                                     detected_version)
                    else:
                        pass #TODO

            factory.protocol = PingProtocol
            factory.connect(host, port, "status")

    def stopFactory(self):
        if self.profile is not None and self.profile.logged_in:
            self.profile.invalidate()
