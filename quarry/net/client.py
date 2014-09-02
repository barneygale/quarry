from twisted.internet import reactor, protocol, defer

from quarry.net.protocol import Factory, Protocol, ProtocolError, \
    protocol_modes_inv, register
from quarry.mojang import auth
from quarry.util import crypto


class ClientProtocol(Protocol):
    """This class represents a connection to a server"""

    protocol_mode_next = "login"

    def __init__(self, factory, addr):
        Protocol.__init__(self, factory, addr)

    ### Convenience functions -------------------------------------------------

    def switch_protocol_mode(self, mode):
        self.check_protocol_mode_switch(mode)

        if mode in ("status", "login"):
            # Send handshake
            self.send_packet(0,
                self.buff_type.pack_varint(self.factory.protocol_version) +
                self.buff_type.pack_string(self.recv_addr.host) +
                self.buff_type.pack('H', self.recv_addr.port) +
                self.buff_type.pack_varint(
                    protocol_modes_inv[self.protocol_mode_next]))

        self.protocol_mode = mode

        if mode == "status":
            # Send status request
            self.send_packet(0)

        elif mode == "login":
            # Send login start
            self.send_packet(0, self.buff_type.pack_string(
                self.factory.profile.username))


    ### Callbacks -------------------------------------------------------------

    def connection_made(self):
        Protocol.connection_made(self)
        self.switch_protocol_mode(self.protocol_mode_next)

    def auth_ok(self, data):
        # Send encryption response
        p_shared_secret = crypto.encrypt_secret(
            self.public_key,
            self.shared_secret)
        p_verify_token = crypto.encrypt_secret(
            self.public_key,
            self.verify_token)

        # 1.7.x
        if self.factory.protocol_version <= 5:
            self.send_packet(1,
                self.buff_type.pack('h', len(p_shared_secret)) +
                self.buff_type.pack_raw(p_shared_secret) +
                self.buff_type.pack('h', len(p_verify_token)) +
                self.buff_type.pack_raw(p_verify_token))
        # 1.8.x
        else:
            self.send_packet(1,
            self.buff_type.pack_varint(len(p_shared_secret)) +
            self.buff_type.pack_raw(p_shared_secret) +
            self.buff_type.pack_varint(len(p_verify_token)) +
            self.buff_type.pack_raw(p_verify_token))

        # Enable encryption
        self.cipher.enable(self.shared_secret)
        self.logger.debug("Encryption enabled")

    def player_joined(self):
        Protocol.player_joined(self)
        self.logger.info("Joined the game.")

    def player_left(self):
        Protocol.player_left(self)
        self.logger.info("Left the game.")

    ### Packet handlers -------------------------------------------------------

    @register("login", 0x00)
    def packet_kick(self, buff):
        p_data = buff.unpack_chat()
        self.logger.warn("Kicked: %s" % p_data)
        self.close()

    @register("login", 0x01)
    def packet_encryption_request(self, buff):
        p_server_id    = buff.unpack_string()

        # 1.7.x
        if self.factory.protocol_version <= 5:
            p_public_key   = buff.unpack_raw(buff.unpack('h'))
            p_verify_token = buff.unpack_raw(buff.unpack('h'))
        # 1.8.x
        else:
            p_public_key   = buff.unpack_raw(buff.unpack_varint())
            p_verify_token = buff.unpack_raw(buff.unpack_varint())

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
        p_uuid = buff.unpack_string()
        p_username = buff.unpack_string()

        self.switch_protocol_mode("play")
        self.player_joined()

    @register("login", 0x03)
    def packet_set_compression(self, buff):
        self.compression_threshold = buff.unpack_varint()
        self.compression_enabled = True

        self.logger.debug("Compression enabled (%d byte threshold)" % self.compression_threshold)

class ClientFactory(Factory, protocol.ClientFactory):
    protocol = ClientProtocol
    protocol_version = 5
    profile = None

    def connect(self, addr, port=25565):
        reactor.connectTCP(addr, port, self, self.connection_timeout)

class AgnosticClientProtocol(ClientProtocol):
    protocol_mode_next = "status"

    @register("status", 0x00)
    def packet_status_response(self, buff):
        p_response = buff.unpack_json()
        p_version = int(p_response["version"]["protocol"])

        self.factory.version_request.callback(p_version)

class AgnosticClientFactory(ClientFactory):
    def connect(self, addr, port=25565):
        def _callback(protocol_version):
            if protocol_version in self.protocol_versions:
                self.protocol_version = protocol_version
                ClientFactory.connect(self, addr, port)
            else:
                pass #TODO

        factory = ClientFactory()
        factory.protocol = AgnosticClientProtocol
        factory.version_request = defer.Deferred()
        factory.version_request.addCallback(_callback)
        factory.connect(addr, port)