import logging

from quarry.net.server import ServerFactory, ServerProtocol
from quarry.net.client import ClientFactory, ClientProtocol
from quarry.mojang.profile import Profile
from quarry.util.dispatch import PacketDispatcher, register


class ProxyClientProtocol(ClientProtocol):
    def packet_received_passthrough(self, buff, ident):
        self.log_packet(". recv", ident)
        self.factory.bridge.packet_received(
            buff,
            self.protocol_mode,
            ident,
            "upstream")

    def enable_passthrough(self):
        self.packet_received = self.packet_received_passthrough

    def setup(self):
        self.factory.bridge.upstream = self

    def player_joined(self):
        self.factory.bridge.upstream_connected()

    def connection_lost(self, reason=None):
        ClientProtocol.connection_lost(self, reason)
        self.factory.bridge.upstream_disconnected()


class ProxyClientFactory(ClientFactory):
    protocol = ProxyClientProtocol
    bridge = None


class Bridge(PacketDispatcher):
    downstream_factory  = None
    downstream = None
    upstream_factory  = None
    upstream = None

    buff_type = None

    log_level = logging.INFO

    def __init__(self, server_factory, server_protocol):
        self.downstream_factory  = server_factory
        self.upstream_factory    = server_factory.client_factory_class()
        self.downstream = server_protocol
        self.upstream   = None

        self.buff_type = self.downstream_factory.buff_type

        self.logger = logging.getLogger("%s{%s}" % (
            self.__class__.__name__,
            self.downstream.username))
        self.logger.setLevel(self.log_level)

        self.register_handlers()

        # Set up offline profile
        profile = Profile()
        profile.login_offline(self.downstream.username)

        # Set up client factory
        self.upstream_factory.bridge = self
        self.upstream_factory.profile = profile
        self.upstream_factory.protocol_version = \
            self.downstream.protocol_version

        # Connect!
        self.upstream_factory.connect(
            server_factory.connect_host,
            server_factory.connect_port)

    def upstream_connected(self):
        self.downstream.enable_passthrough()
        self.upstream.enable_passthrough()

    def upstream_disconnected(self):
        self.downstream.close("Lost connection to server.")

    def downstream_disconnected(self):
        if self.upstream:
            self.upstream.close()

    def packet_received(self, buff, protocol_mode, ident, direction):
        dispatched = self.dispatch((protocol_mode, ident, direction), buff)

        if not dispatched:
            self.packet_unhandled(buff, protocol_mode, ident, direction)

    def packet_unhandled(self, buff, protocol_mode, ident, direction):
        if direction == "upstream":
            self.downstream.send_packet(ident, buff.unpack_all())
        elif direction == "downstream":
            self.upstream.send_packet(ident, buff.unpack_all())


class ProxyServerProtocol(ServerProtocol):
    bridge = None

    def packet_received_passthrough(self, buff, ident):
        self.bridge.packet_received(
            buff,
            self.protocol_mode,
            ident,
            "downstream")

    def enable_passthrough(self):
        self.packet_received = self.packet_received_passthrough

    def player_joined(self):
        ServerProtocol.player_joined(self)
        self.bridge = self.factory.bridge_class(self.factory, self)

    def connection_lost(self, reason=None):
        ServerProtocol.connection_lost(self, reason)
        if self.bridge:
            self.bridge.downstream_disconnected()


class ProxyServerFactory(ServerFactory):
    protocol = ProxyServerProtocol
    client_factory_class = ProxyClientFactory
    connect_host = None
    connect_port = None
    bridge_class = Bridge
