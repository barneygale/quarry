from twisted.internet import reactor, protocol, defer

from quarry.net.protocol import Factory, Protocol, ProtocolError, \
    protocol_modes_inv, register
from quarry.mojang import auth
from quarry.util import crypto


class ClientProtocol(Protocol):
    """This class represents a connection to a server"""

    protocol_mode_next = None

    def __init__(self, factory, addr):
        Protocol.__init__(self, factory, addr)

    ### Convenience functions -------------------------------------------------

    def switch_protocol_mode(self, mode):
        self.check_protocol_mode_switch(mode)

        if mode in ("status", "login"):
            # Send handshake
            addr = self.transport.connector.getDestination()
            self.send_packet(0,
                self.buff_type.pack_varint(self.protocol_version) +
                self.buff_type.pack_string(addr.host) +
                self.buff_type.pack('H', addr.port) +
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
        if self.protocol_version <= 5:
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

    def status_response(self, data):
        self.close()

    ### Packet handlers -------------------------------------------------------

    @register("status", 0x00)
    def packet_status_response(self, buff):
        p_data = buff.unpack_json()
        self.status_response(p_data)

    @register("login", 0x00)
    def packet_kick(self, buff):
        p_data = buff.unpack_chat()
        self.logger.warn("Kicked: %s" % p_data)
        self.close()

    @register("login", 0x01)
    def packet_encryption_request(self, buff):
        p_server_id    = buff.unpack_string()

        # 1.7.x
        if self.protocol_version <= 5:
            p_public_key   = buff.read(buff.unpack('h'))
            p_verify_token = buff.read(buff.unpack('h'))
        # 1.8.x
        else:
            p_public_key   = buff.read(buff.unpack_varint())
            p_verify_token = buff.read(buff.unpack_varint())

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
    def packet_login_set_compression(self, buff):
        self.set_compression(buff.unpack_varint())

    @register("play", 0x46)
    def packet_play_set_compression(self, buff):
        self.set_compression(buff.unpack_varint())

class ClientFactory(Factory, protocol.ClientFactory):
    protocol = ClientProtocol
    profile = None

    def connect(self, host, port=25565, protocol_mode_next="login",
                protocol_version=0):

        if protocol_mode_next == "status" or protocol_version > 0:
            self.protocol.protocol_mode_next = protocol_mode_next
            self.protocol.protocol_version = protocol_version
            reactor.connectTCP(host, port, self, self.connection_timeout)

        else:
            factory = ClientFactory()
            class PingProtocol(factory.protocol):
                def status_response(s, data):
                    s.close()
                    detected_version = int(data["version"]["protocol"])
                    if detected_version in self.protocol_versions:
                        self.connect(host, port, protocol_mode_next,
                                     detected_version)
                    else:
                        pass #TODO

            factory.protocol = PingProtocol
            factory.connect(host, port, "status")