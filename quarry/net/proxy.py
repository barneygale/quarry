from quarry.net.server import ServerFactory, ServerProtocol
from quarry.net.client import ClientFactory, ClientProtocol
from quarry.mojang.profile import Profile

# This isn't finished
# The idea is to let you filter packets and only send what you want

class ProxyClientProtocol(ClientProtocol):
    def packet_received_passthrough(self, buff, ident):
        buff.save()
        consumed = ClientProtocol.packet_received(self, buff, ident)
        if not consumed:
            buff.restore()
            self.factory.server_protocol.send_packet(ident, buff.unpack_all())

    def enable_passthrough(self):
        self.packet_received = self.packet_received_passthrough

    def setup(self):
        self.factory.client_protocol = self

    def player_joined(self):
        self.factory.enable_passthrough()

class ProxyServerProtocol(ServerProtocol):
    def packet_received_passthrough(self, buff, ident):
        buff.save()
        consumed = ServerProtocol.packet_received(self, buff, ident)
        if not consumed:
            buff.restore()
            self.client_factory.client_protocol.send_packet(
                ident,
                buff.unpack_all())

    def enable_passthrough(self):
        self.packet_received = self.packet_received_passthrough

    def player_joined(self):
        ServerProtocol.player_joined(self)

        profile = Profile()
        profile.login_offline(self.username)

        self.client_factory = self.factory.client_factory_class()
        self.client_factory.profile = profile
        self.client_factory.server_protocol = self
        self.client_factory.connect(
            self.factory.connect_host,
            self.factory.connect_port)

class ProxyClientFactory(ClientFactory):
    protocol = ProxyClientProtocol
    server_protocol = None
    client_protocol = None

    def enable_passthrough(self):
        self.server_protocol.enable_passthrough()
        self.client_protocol.enable_passthrough()

class ProxyServerFactory(ServerFactory):
    protocol = ProxyServerProtocol
    client_factory_class = ProxyClientFactory
    connect_host = None
    connect_port = None