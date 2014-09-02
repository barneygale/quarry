import logging

from quarry.net.server import ServerFactory, ServerProtocol
from quarry.net.client import ClientFactory, ClientProtocol
from quarry.mojang.profile import Profile
from quarry.util.dispatch import PacketDispatcher, register

#
# Rough diagram of the universe a quarry proxy usually operates in:
#               .
# outside world . server box
#               .
#  +--------+   .   +--------------------------------+       +--------+
#  | mojang | ----> |              QUARRY            | ----> | mojang |
#  | client | <---- | downstream | bridge | upstream | <---- | server |
#  +--------+   .   +--------------------------------+       +--------+
#               .          ^                   ^
#               .        server              client
#               .    (online mode)       (offline mode)
#               .
#
# A quarry proxy has three main parts:
#  * The "downstream" (a server) which connects with the mojang client
#  * The "upstream" (a client) which connects with the mojang server
#  * The "bridge", which handles packet-passing between the above
#
# The downstream and upstream are broken down into two parts:
#  * DownstreamFactory - program-wide object that spawns a Downtime object for
#      each incoming connection
#  * Downstream - connection with the external client.
#  * UpstreamFactory - a simple class that spawns an Upstream
#  * Upstream - connection with the external server.
#
# When the user connects, the DownstreamFactory creates a Downstream object
#   to communicate with the external client. If we're running in online-mode,
#   we go through auth with mojang. Once the user is authed, we spawn
#   a Bridge object, which in turn spawns a UpstreamFactory. When the
#   connection is made external server, an Upstream object tells the Bridge
#   to enable "pass-through" mode. At this point, the Upstream and Downstream
#   are connected and exchange packets.
#
# You can inspect, drop, modify and forge packets in-transit by registering
#   handlers in the Bridge.
#

class Upstream(ClientProtocol):
    def packet_received_passthrough(self, buff, ident):
        self.log_packet(". recv", ident)
        self.factory.bridge.packet_received(
            buff,
            self.protocol_mode,
            ident,
            "downstream")

    def enable_passthrough(self):
        self.packet_received = self.packet_received_passthrough

    def setup(self):
        self.factory.bridge.upstream = self

    def player_joined(self):
        self.factory.bridge.upstream_connected()

    def connection_lost(self, reason=None):
        ClientProtocol.connection_lost(self, reason)
        self.factory.bridge.upstream_disconnected()


class UpstreamFactory(ClientFactory):
    protocol = Upstream
    bridge = None


class Bridge(PacketDispatcher):
    downstream_factory = None
    upstream_factory   = None
    downstream = None
    upstream   = None

    buff_type = None

    log_level = logging.INFO

    def __init__(self, downstream_factory, downstream):
        self.downstream_factory  = downstream_factory
        self.upstream_factory    = downstream_factory.upstream_factory_class()
        self.downstream = downstream
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
        self.upstream_factory.buff_type = self.buff_type
        self.upstream_factory.profile = profile
        self.upstream_factory.protocol.protocol_version = \
            self.downstream.protocol_version

        # Connect!
        self.upstream_factory.connect(
            self.downstream_factory.connect_host,
            self.downstream_factory.connect_port)

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
        if direction == "downstream":
            self.downstream.send_packet(ident, buff.unpack_all())
        elif direction == "upstream":
            self.upstream.send_packet(ident, buff.unpack_all())


class Downstream(ServerProtocol):
    bridge = None

    def packet_received_passthrough(self, buff, ident):
        self.bridge.packet_received(
            buff,
            self.protocol_mode,
            ident,
            "upstream")

    def enable_passthrough(self):
        self.packet_received = self.packet_received_passthrough

    def player_joined(self):
        ServerProtocol.player_joined(self)
        self.bridge = self.factory.bridge_class(self.factory, self)

    def connection_lost(self, reason=None):
        ServerProtocol.connection_lost(self, reason)
        if self.bridge:
            self.bridge.downstream_disconnected()


class DownstreamFactory(ServerFactory):
    protocol = Downstream
    upstream_factory_class = UpstreamFactory
    connect_host = None
    connect_port = None
    bridge_class = Bridge
