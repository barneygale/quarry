from twisted.internet import reactor, protocol

from quarry import crypto
from quarry.buffer import Buffer
from quarry.net.protocol import Factory, Protocol, ProtocolError, \
    protocol_modes_inv, register
from quarry.mojang import auth


class ClientProtocol(Protocol):
    """This class represents a connection to a server"""

    protocol_mode_next = "login"

    def __init__(self, factory, addr):
        Protocol.__init__(self, factory, addr)

    ### Callbacks -------------------------------------------------------------

    def auth_ok(self, data):
        # Send encryption response
        self.send_packet(1,
            Buffer.pack_array(crypto.encrypt_secret(
                self.public_key,
                self.shared_secret)) +
            Buffer.pack_array(crypto.encrypt_secret(
                self.public_key,
                self.verify_token)))

        # Enable encryption
        self.cipher.enable(self.shared_secret)

    ### Packet handlers -------------------------------------------------------

    def connectionMade(self):
        # Send handshake
        self.send_packet(0,
            Buffer.pack_varint(self.factory.protocol_version) +
            Buffer.pack_string(self.recv_addr.host) +
            Buffer.pack('H', self.recv_addr.port) +
            Buffer.pack_varint(protocol_modes_inv[self.protocol_mode_next]))

        self.protocol_mode = self.protocol_mode_next

        if self.protocol_mode == "status":
            # Send status request
            self.send_packet(0)

        elif self.protocol_mode == "login":
            # Send login start
            self.send_packet(0, Buffer.pack_string(
                self.factory.profile.username))

    @register("login", 0x00)
    def packet_kick(self, buff):
        p_data = buff.unpack_json()
        self.logger.warn("Kicked: %s" % p_data)
        self.close()

    @register("login", 0x01)
    def packet_encryption_request(self, buff):
        p_server_id    = buff.unpack_string()
        p_public_key   = buff.unpack_array()
        p_verify_token = buff.unpack_array()

        if not self.factory.profile.logged_in:
            raise ProtocolError("Can't log into online-mode server while using"
                                " offline profile")

        self.shared_secret = crypto.make_shared_secret()
        self.public_key = crypto.import_public_key(p_public_key)
        self.verify_token  = p_verify_token

        # make digest
        digest = crypto.make_digest(
            p_server_id,
            self.shared_secret,
            p_public_key)

        # do auth
        deferred = auth.join(
            self.factory.auth_timeout,
            digest,
            self.factory.profile.access_token,
            self.factory.profile.uuid)
        deferred.addCallbacks(self.auth_ok, self.auth_failed)

    @register("login", 0x02)
    def packet_login_success(self, buff):
        buff.discard()

        self.protocol_mode = "play"
        self.player_joined()


class ClientFactory(Factory, protocol.ClientFactory):
    protocol = ClientProtocol

    profile = None

    def connect(self, addr, port=25565):
        reactor.connectTCP(addr, port, self, self.connection_timeout)