import logging

from quarry.net.protocol import PacketDispatcher
from quarry.net.server import ServerFactory, ServerProtocol
from quarry.net.client import ClientFactory, ClientProtocol
from quarry.net.auth import OfflineProfile


def _enable_forwarding(endpoint):
    """
    Patches the given endpoint's ``packet_received()`` method to pass packets
    through the bridge.
    """
    def packet_received(buff, name):
        endpoint.bridge.packet_received(
            buff,
            endpoint.recv_direction,
            name)
    endpoint._packet_received = endpoint.packet_received
    endpoint.packet_received = packet_received


def _disable_forwarding(endpoint):
    """
    Patches the given endpoint's ``packet_received()`` method to restore
    handling of packets within the endpoint.
    """
    endpoint.packet_received = endpoint._packet_received


def _enable_fast_forwarding(endpoint1, endpoint2):
    """
    Patches the first given endpoint's ``data_received()`` method to network
    data directly to the second endpoint, without any packet decoding.
    """
    if len(endpoint1.recv_buff) > 0:
        endpoint2.transport.write(
            endpoint2.cipher.encrypt(
                endpoint1.recv_buff.read()))

    def data_received(data):
        endpoint2.transport.write(
            endpoint2.cipher.encrypt(
                endpoint1.cipher.decrypt(data)))

    endpoint1.data_received = data_received


class Upstream(ClientProtocol):
    def setup(self):
        self.bridge = self.factory.bridge
        self.bridge.upstream = self

    def player_joined(self):
        self.bridge.upstream_ready()

    def connection_lost(self, reason=None):
        ClientProtocol.connection_lost(self, reason)
        self.bridge.upstream_disconnected()


class UpstreamFactory(ClientFactory):
    protocol = Upstream
    bridge = None


class Bridge(PacketDispatcher):
    """
    This class exchanges packets between the upstream and downstream.
    """

    upstream_factory_class = UpstreamFactory
    log_level = logging.INFO

    logger = None
    buff_type = None

    downstream_factory = None
    downstream = None

    upstream_profile = None
    upstream_factory = None
    upstream = None

    def __init__(self, downstream_factory, downstream):
        self.downstream_factory = downstream_factory
        self.downstream = downstream

        self.buff_type = self.downstream.buff_type

        self.logger = logging.getLogger("%s{%s}" % (
            self.__class__.__name__,
            self.downstream.remote_addr.host))
        self.logger.setLevel(self.log_level)

    def make_profile(self):
        """
        Returns the profile to use for the upstream connection. By default, use
        an offline profile with the same display name as the remote client.
        """
        return OfflineProfile(self.downstream.display_name)

    def connect(self):
        """
        Connect to the remote server.
        """

        self.upstream_profile = self.make_profile()
        self.upstream_factory = self.upstream_factory_class(
            self.upstream_profile)
        self.upstream_factory.bridge = self
        self.upstream_factory.force_protocol_version = \
            self.downstream.protocol_version
        self.upstream_factory.connect(
            self.connect_host,
            self.connect_port)

    # Connections -------------------------------------------------------------

    def downstream_ready(self):
        """
        Called when the downstream is waiting for forwarding to begin.
        By default, this method begins a connection to the remote server.
        """

        self.logger.debug("Downstream ready")

        # Connect to the server the client is requesting
        if self.downstream_factory.connect_host is None:
            self.connect_host = self.downstream.connect_host
            self.connect_port = self.downstream.connect_port
        else:
            self.connect_host = self.downstream_factory.connect_host
            self.connect_port = self.downstream_factory.connect_port

        self.connect()

    def upstream_ready(self):
        """
        Called when the upstream is waiting for forwarding to begin. By
        default, enables forwarding.
        """
        self.logger.debug("Upstream ready")
        self.enable_forwarding()

    def downstream_disconnected(self):
        """
        Called when the connection to the remote client is closed.
        """
        if self.upstream:
            self.upstream.close()

    def upstream_disconnected(self):
        """
        Called when the connection to the remote server is closed.
        """
        self.downstream.close("Lost connection to server.")

    # Pass through ------------------------------------------------------------

    def enable_forwarding(self):
        """
        Enables forwarding. Packet handlers in the ``Upstream`` and
        ``Downstream`` cease to be called, and all packets are routed via the
        ``Bridge``. This method is called by ``upstream_ready()`` by default.
        """

        _enable_forwarding(self.downstream)
        _enable_forwarding(self.upstream)
        self.logger.debug("Forwarding enabled")

    def disable_forwarding(self):
        """
        Disable forwarding. Packet handlers in the ``Bridge`` cease to be
        called, and packets are routed via the ``Upstream`` and ``Downstream``.
        This method is not called by default.
        """

        _disable_forwarding(self.downstream)
        _disable_forwarding(self.upstream)
        self.logger.debug("Forwarding disabled")

    def enable_fast_forwarding(self):
        """
        Enables fast forwarding. Quarry passes network data between endpoints
        without decoding packets, and therefore all packet handlers cease to be
        called. Both parts of the proxy must be operating at the same
        compression threshold. This method is not called by default.
        """
        if self.downstream.compression_threshold != \
                self.upstream.compression_threshold:
            raise Exception(
                "Cannot enable fast forwarding as compression differs. "
                "downstream: %s, upstream: %s" % (
                    self.downstream.compression_threshold,
                    self.upstream.compression_threshold))

        _enable_fast_forwarding(self.downstream, self.upstream)
        _enable_fast_forwarding(self.upstream, self.downstream)
        self.logger.debug("Fast forwarding enabled")

    # Packet handling ---------------------------------------------------------

    def packet_received(self, buff, direction, name):
        """
        Called when a packet is received a remote. Usually this method
        dispatches the packet to a method named
        ``packet_<direction>_<packet name>``, or calls :meth:`packet_unhandled`
        if no such methods exists. You might want to override this to implement
        your own dispatch logic or logging.
        """

        dispatched = self.dispatch((direction, name), buff)

        if not dispatched:
            self.packet_unhandled(buff, direction, name)

    def packet_unhandled(self, buff, direction, name):
        """
        Called when a packet is received that is not hooked. The default
        implementation forwards the packet.
        """
        if direction == "downstream":
            self.downstream.send_packet(name, buff.read())
        elif direction == "upstream":
            self.upstream.send_packet(name, buff.read())

    def packet_downstream_set_compression(self, buff):
        self.upstream.set_compression(buff.unpack_varint())


class Downstream(ServerProtocol):
    bridge = None

    def setup(self):
        self.bridge = self.factory.bridge_class(self.factory, self)

    def player_joined(self):
        ServerProtocol.player_joined(self)
        self.bridge.downstream_ready()

    def connection_lost(self, reason=None):
        ServerProtocol.connection_lost(self, reason)
        self.bridge.downstream_disconnected()


class DownstreamFactory(ServerFactory):
    protocol = Downstream
    connect_host = None
    connect_port = None
    bridge_class = Bridge
