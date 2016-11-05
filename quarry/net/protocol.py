import string
import sys
import logging
import zlib
from twisted.internet import protocol, reactor

from quarry.data import packets
from quarry.utils.crypto import Cipher
from quarry.utils.buffer import Buffer, BufferUnderrun
from quarry.utils.errors import ProtocolError
from quarry.utils.tasks import Tasks

PY3 = sys.version_info > (3,)

logging.basicConfig(format="%(name)s | %(levelname)s | %(message)s")

protocol_modes = {
    0: 'init',
    1: 'status',
    2: 'login',
    3: 'play'
}
protocol_modes_inv = dict(((v, k) for k, v in protocol_modes.items()))


class PacketDispatcher(object):
    def dispatch(self, lookup_args, buff):
        handler = getattr(self, "packet_%s" % "_".join(lookup_args), None)
        if handler is not None:
            handler(buff)
            return True
        return False

    def dump_packet(self, data):
        lines = ['Packet dump:']
        bytes_read = 0
        while len(data) > 0:
            data_line, data = data[:16], data[16:]

            l_hex = []
            l_str = []
            for i, c in enumerate(data_line):
                if PY3:
                    l_hex.append("%02x" % c)
                    c_str = data_line[i:i+1]
                    l_str.append(c_str if c_str in string.printable else ".")
                else:
                    l_hex.append("%02x" % ord(c))
                    l_str.append(c if c in string.printable else ".")

            l_hex.extend(['  '] * (16 - len(l_hex)))
            l_hex.insert(8, '')

            lines.append("%08x  %s  |%s|" % (
                bytes_read,
                " ".join(l_hex),
                "".join(l_str)))

            bytes_read += len(data_line)

        return "\n    ".join(lines + ["%08x" % bytes_read])


class Protocol(protocol.Protocol, PacketDispatcher, object):
    """Shared logic between the client and server"""

    #: Usually a reference to the :class:`Buffer` class. This is useful when
    #: constructing a packet payload for use in :meth:`send_packet`
    buff_type = None

    #: A reference to the logger
    logger = None

    #: A reference to a :class:`Tasks` instance. This object has methods for
    #: setting up repeating or delayed callbacks
    tasks = None

    recv_direction = None
    send_direction = None
    protocol_version = packets.default_protocol_version
    protocol_mode = "init"
    compression_threshold = None
    compression_enabled = False
    in_game = False
    closed = False

    def __init__(self, factory, remote_addr):
        self.factory = factory
        self.remote_addr = remote_addr

        self.buff_type = self.factory.buff_type
        self.recv_buff = self.buff_type()
        self.cipher = Cipher()
        self.tasks = Tasks()

        self.logger = logging.getLogger("%s{%s}" % (
            self.__class__.__name__,
            self.remote_addr.host))
        self.logger.setLevel(self.factory.log_level)

        self.connection_timer = self.tasks.add_delay(
            self.factory.connection_timeout,
            self.connection_timed_out)

        self.setup()

    ### Fix ugly twisted methods ----------------------------------------------

    def dataReceived(self, data):
        return self.data_received(data)

    def connectionMade(self):
        return self.connection_made()

    def connectionLost(self, reason=None):
        return self.connection_lost(reason)

    ### Convenience functions -------------------------------------------------

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
        if not self.compression_enabled:
            self.compression_enabled = True
            self.logger.debug("Compression enabled")

        self.compression_threshold = compression_threshold
        self.logger.debug("Compression threshold set to %d bytes" % compression_threshold)

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

    ### General callbacks -----------------------------------------------------

    def setup(self):
        """Called when the Protocol's initialiser is finished"""

        pass

    def protocol_error(self, err):
        """Called when a protocol error occurs"""

        msg = "Protocol error: %s" % err
        self.logger.error(msg)
        self.close(msg)

    ### Connection callbacks --------------------------------------------------

    def connection_made(self):
        """Called when the connection is established"""

        self.logger.debug("Connection made")

    def connection_lost(self, reason=None):
        """Called when the connection is lost"""

        self.closed = True
        if self.in_game:
            self.player_left()
        self.logger.debug("Connection lost")

        self.tasks.stop_all()

    def connection_timed_out(self):
        """Called when the connection has been idle too long"""

        self.close("Connection timed out")

    ### Auth callbacks --------------------------------------------------------

    def auth_ok(self, data):
        """Called when auth with mojang succeeded (online mode only)"""

        pass

    def auth_failed(self, err):
        """Called when auth with mojang failed (online mode only)"""

        self.logger.warn("Auth failed: %s" % err.value)
        self.close("Auth failed: %s" % err.value)

    ### Player callbacks ------------------------------------------------------

    def player_joined(self):
        """Called when the player joins the game"""

        self.in_game = True

    def player_left(self):
        """Called when the player leaves the game"""

        pass

    ### Packet handling -------------------------------------------------------

    def data_received(self, data):
        # Decrypt data
        data = self.cipher.decrypt(data)

        # Add it to our buffer
        self.recv_buff.add(data)

        # Read some packets
        while not self.closed:
            # Save the buffer, in case we read an incomplete packet
            self.recv_buff.save()

            # Try to read a packet
            try:
                max_bits = 32 if self.protocol_mode == "play" else 21
                packet_length = self.recv_buff.unpack_varint(max_bits=max_bits)
                packet_body = self.recv_buff.read(packet_length)

            # Incomplete packet read, restore the buffer.
            except BufferUnderrun:
                self.recv_buff.restore()
                break

            # Load the packet body into a buffer
            packet_buff = self.buff_type()
            packet_buff.add(packet_body)

            try:  # Catch protocol errors
                try:  # Catch buffer overrun/underrun
                    if self.compression_enabled:
                        uncompressed_length = packet_buff.unpack_varint()

                        if uncompressed_length > 0:
                            data = zlib.decompress(packet_buff.read())
                            packet_buff = Buffer()
                            packet_buff.add(data)
                    ident = packet_buff.unpack_varint()
                    key = (
                        self.protocol_version,
                        self.protocol_mode,
                        self.recv_direction,
                        ident)
                    try:
                        name = packets.packet_names[key]
                    except KeyError:
                        raise ProtocolError("No name known for packet: %s"
                                            % (key,))
                    self.packet_received(packet_buff, name)

                except BufferUnderrun:
                    raise ProtocolError("Packet is too short!")

                if len(packet_buff) > 0:
                    raise ProtocolError("Packet is too long!")

            except ProtocolError as e:
                self.protocol_error(e)
                break

            # We've read a complete packet, so reset the inactivity timeout
            self.connection_timer.restart()

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

    def send_packet(self, name, data=b""):
        """Sends a packet to the remote."""

        if self.closed:
            return

        self.log_packet("# send", name)

        # Prepend ident
        key = (
            self.protocol_version,
            self.protocol_mode,
            self.send_direction,
            name)
        try:
            ident = packets.packet_idents[key]
        except KeyError:
            raise ProtocolError("No ID known for packet: %s" % (key,))
        data = Buffer.pack_varint(ident) + data

        if self.compression_enabled:
            # Compress data and prepend uncompressed data length
            if len(data) >= self.compression_threshold:
                data = Buffer.pack_varint(len(data)) + zlib.compress(data)
            else:
                data = Buffer.pack_varint(0) + data

        # Prepend packet length
        max_bits = 32 if self.protocol_mode == "play" else 21
        data = self.buff_type.pack_varint(len(data), max_bits=max_bits) + data

        # Encrypt
        data = self.cipher.encrypt(data)

        # Send
        self.transport.write(data)


class Factory(protocol.Factory, object):
    protocol = Protocol
    buff_type = Buffer
    log_level = logging.INFO
    connection_timeout = 30

    minecraft_versions = packets.minecraft_versions

    def buildProtocol(self, addr):
        return self.protocol(self, addr)