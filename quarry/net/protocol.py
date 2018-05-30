import logging
from twisted.internet import protocol

from quarry.data import packets
from quarry.types.buffer import BufferUnderrun, buff_types
from quarry.net.crypto import Cipher
from quarry.net.ticker import Ticker

logging.basicConfig(format="%(name)s | %(levelname)s | %(message)s")

protocol_modes = {
    0: 'init',
    1: 'status',
    2: 'login',
    3: 'play'
}
protocol_modes_inv = dict(((v, k) for k, v in protocol_modes.items()))


class ProtocolError(Exception):
    pass


class PacketDispatcher(object):
    def dispatch(self, lookup_args, buff):
        handler = getattr(self, "packet_%s" % "_".join(lookup_args), None)
        if handler is not None:
            handler(buff)
            return True
        return False


class Protocol(protocol.Protocol, PacketDispatcher, object):
    """Shared logic between the client and server"""

    #: Usually a reference to a :class:`Buffer` class. This is useful when
    #: constructing a packet payload for use in :meth:`send_packet`
    buff_type = None

    #: The logger for this protocol.
    logger = None

    #: A reference to a :class:`Ticker` instance.
    ticker = None

    #: A reference to the factory
    factory = None

    #: The IP address of the remote.
    remote_addr = None

    recv_direction = None
    send_direction = None
    protocol_version = packets.default_protocol_version
    protocol_mode = "init"
    compression_threshold = -1
    in_game = False
    closed = False

    def __init__(self, factory, remote_addr):
        self.factory = factory
        self.remote_addr = remote_addr

        self.buff_type = self.factory.get_buff_type(self.protocol_version)
        self.recv_buff = self.buff_type()
        self.cipher = Cipher()

        self.logger = logging.getLogger("%s{%s}" % (
            self.__class__.__name__,
            self.remote_addr.host))
        self.logger.setLevel(self.factory.log_level)

        self.ticker = self.factory.ticker_type(self.logger)
        self.ticker.start()

        self.connection_timer = self.ticker.add_delay(
            delay=self.factory.connection_timeout / self.ticker.interval,
            callback=self.connection_timed_out)

        self.setup()

    # Fix ugly twisted methods ------------------------------------------------

    def dataReceived(self, data):
        return self.data_received(data)

    def connectionMade(self):
        return self.connection_made()

    def connectionLost(self, reason=None):
        return self.connection_lost(reason)

    # Convenience functions ---------------------------------------------------

    def check_protocol_mode_switch(self, mode):
        transitions = [
            ("init", "status"),
            ("init", "login"),
            ("login", "play")
        ]

        if (self.protocol_mode, mode) not in transitions:
            raise ProtocolError("Cannot switch protocol mode from %s to %s"
                                % (self.protocol_mode, mode))

    def switch_protocol_mode(self, mode):
        self.check_protocol_mode_switch(mode)
        self.protocol_mode = mode

    def set_compression(self, compression_threshold):
        self.compression_threshold = compression_threshold
        self.logger.debug("Compression threshold set to %d bytes"
                          % compression_threshold)

    def close(self, reason=None):
        """Closes the connection"""

        if not self.closed:
            if reason:
                reason = "Closing connection: %s" % reason
            else:
                reason = "Closing connection"

            if self.in_game:
                self.logger.info(reason)
            else:
                self.logger.debug(reason)

            self.transport.loseConnection()
            self.closed = True

    def log_packet(self, prefix, name):
        """Logs a packet at debug level"""

        self.logger.debug("Packet %s %s/%s" % (
            prefix,
            self.protocol_mode,
            name))

    # General callbacks -------------------------------------------------------

    def setup(self):
        """Called when the Protocol's initialiser is finished"""

        pass

    def protocol_error(self, err):
        """Called when a protocol error occurs"""

        self.logger.exception(err)
        self.close("Protocol error")

    # Connection callbacks ----------------------------------------------------

    def connection_made(self):
        """Called when the connection is established"""

        self.logger.debug("Connection made")

    def connection_lost(self, reason=None):
        """Called when the connection is lost"""

        self.closed = True
        if self.in_game:
            self.player_left()
        self.logger.debug("Connection lost")

        self.ticker.stop()

    def connection_timed_out(self):
        """Called when the connection has been idle too long"""

        self.close("Connection timed out")

    # Auth callbacks ----------------------------------------------------------

    def auth_ok(self, data):
        """Called when auth with mojang succeeded (online mode only)"""

        pass

    def auth_failed(self, err):
        """Called when auth with mojang failed (online mode only)"""

        self.logger.warning("Auth failed: %s" % err.value)
        self.close("Auth failed: %s" % err.value)

    # Player callbacks --------------------------------------------------------

    def player_joined(self):
        """Called when the player joins the game"""

        self.in_game = True

    def player_left(self):
        """Called when the player leaves the game"""

        pass

    # Packet handling ---------------------------------------------------------

    def get_packet_name(self, ident):
        key = (self.protocol_version, self.protocol_mode, self.recv_direction,
               ident)
        try:
            return packets.packet_names[key]
        except KeyError:
            raise ProtocolError("No name known for packet: %s" % (key,))

    def get_packet_ident(self, name):
        key = (self.protocol_version, self.protocol_mode, self.send_direction,
               name)
        try:
            return packets.packet_idents[key]
        except KeyError:
            raise ProtocolError("No ID known for packet: %s" % (key,))

    def data_received(self, data):
        # Decrypt data
        data = self.cipher.decrypt(data)

        # Add it to our buffer
        self.recv_buff.add(data)

        # Read some packets
        while not self.closed:
            # Save the buffer, in case we read an incomplete packet
            self.recv_buff.save()

            # Read the packet
            try:
                buff = self.recv_buff.unpack_packet(
                    self.buff_type,
                    self.compression_threshold)

            except BufferUnderrun:
                self.recv_buff.restore()
                break

            try:
                # Identify the packet
                name = self.get_packet_name(buff.unpack_varint())

                # Dispatch the packet
                try:
                    self.packet_received(buff, name)
                except BufferUnderrun:
                    raise ProtocolError("Packet is too short: %s" % name)
                if len(buff) > 0:
                    raise ProtocolError("Packet is too long: %s" % name)

                # Reset the inactivity timer
                self.connection_timer.restart()

            except ProtocolError as e:
                self.protocol_error(e)

    def packet_received(self, buff, name):
        """
        Called when a packet is received from the remote. Usually this method
        dispatches the packet to a method named ``packet_<packet name>``, or
        calls :meth:`packet_unhandled` if no such methods exists. You might
        want to override this to implement your own dispatch logic or logging.
        """

        self.log_packet(". recv", name)

        dispatched = self.dispatch((name,), buff)

        if not dispatched:
            self.packet_unhandled(buff, name)

    def packet_unhandled(self, buff, name):
        """
        Called when a packet is received that is not hooked. The default
        implementation silently discards the packet.
        """

        buff.discard()

    def send_packet(self, name, *data):
        """Sends a packet to the remote."""

        if self.closed:
            return

        self.log_packet("# send", name)

        data = b"".join(data)

        # Prepend ident
        data = self.buff_type.pack_varint(self.get_packet_ident(name)) + data

        # Pack packet
        data = self.buff_type.pack_packet(data, self.compression_threshold)

        # Encrypt
        data = self.cipher.encrypt(data)

        # Send
        self.transport.write(data)


class Factory(protocol.Factory, object):
    protocol = Protocol
    ticker_type = Ticker
    log_level = logging.INFO
    connection_timeout = 30
    force_protocol_version = None

    minecraft_versions = packets.minecraft_versions

    def buildProtocol(self, addr):
        return self.protocol(self, addr)

    def get_buff_type(self, protocol_version):
        """
        Gets a buffer type for the given protocol version.
        """
        for ver, cls in reversed(buff_types):
            if protocol_version >= ver:
                return cls
