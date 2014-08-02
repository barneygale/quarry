import logging

from twisted.internet import protocol, reactor

from quarry.crypto import Cipher
from quarry.buffer import Buffer, BufferUnderrun
from quarry.timer import Timer


logging.basicConfig(format="%(name)s | %(levelname)s | %(message)s")

protocol_modes = {
    0: 'init',
    1: 'status',
    2: 'login',
    3: 'play'
}
protocol_modes_inv = dict(((v, k) for k, v in protocol_modes.iteritems()))


# Registers a packet handler by giving it a '_packet_handler' field
def register(protocol_mode, packet_ident):
    def inner(fnc):
        fnc._packet_handler = (protocol_mode, packet_ident)
        return fnc
    return inner


class ProtocolError(Exception):
    pass


class Protocol(protocol.Protocol, object):
    """Shared logic between the client and server"""

    protocol_mode = "init"

    def __init__(self, factory, addr):
        self.factory = factory
        self.recv_addr = addr
        self.recv_buff = Buffer()
        self.cipher = Cipher()

        self.logger = logging.getLogger("%s{%s}" % (
            self.__class__.__name__,
            self.recv_addr.host))
        self.logger.setLevel(self.factory.log_level)

        self.register_handlers()

        self.connection_timer = Timer(
            self.factory.connection_timeout,
            self.connection_timed_out)
        self.connection_timer.start()

        self.setup()

    def register_handlers(self):
        self.packet_handlers = {}

        cls = self.__class__
        for field_name in dir(cls):
            if not field_name.startswith("__"):
                field = getattr(cls, field_name)
                data  = getattr(field, "_packet_handler", None)
                if data:
                    self.packet_handlers[data] = field_name

    ### Convenience functions -------------------------------------------------

    def close(self, reason=None):
        """Closes the connection"""

        if reason:
            self.logger.info("Closing connection: %s" % reason)
        self.connection_timer.stop()
        self.transport.loseConnection()

    def log_packet(self, prefix, ident):
        """Logs a packet at debug level"""

        self.logger.debug("packet %s %s/%02x" % (
            prefix,
            self.protocol_mode,
            ident))

    ### General callbacks -----------------------------------------------------

    def setup(self):
        """Called when the object's initialiser is finished"""

        pass

    ### Auth callbacks --------------------------------------------------------

    def auth_ok(self, data):
        """Called when auth with mojang succeeded (online mode only)"""

        pass

    def auth_failed(self, err):
        """Called when auth with mojang failed (online mode only)"""

        self.close("Auth failed: %s" % err.value)

    ### Player callbacks ------------------------------------------------------

    def player_joined(self):
        """Called when the protocol mode has switched to "play" """

        pass

    def player_left(self):
        """Called when the player leaves"""


        pass

    ### Error callbacks -------------------------------------------------------

    def protocol_error(self, err):
        """Called when a protocol error occurs"""

        self.close("Protocol error: %s" % err)

    def connection_timed_out(self):
        """Called when the connection has been idle too long"""

        self.close("Connection timed out")

    ### Packet handling -------------------------------------------------------

    def dataReceived(self, data):
        # Decrypt data
        data = self.cipher.decrypt(data)

        # Add it to our buffer
        self.recv_buff.add(data)

        # Read some packets
        while True:
            # Save the buffer, in case we read an incomplete packet
            self.recv_buff.save()

            # Try to read a packet
            try:
                packet_length = self.recv_buff.unpack_varint()
                packet_body = self.recv_buff.unpack_raw(packet_length)

            # Incomplete packet read, restore the buffer.
            except BufferUnderrun:
                self.recv_buff.restore()
                break

            # Load the packet body into a buffer
            packet_buff = Buffer()
            packet_buff.add(packet_body)

            try: # Catch protocol errors
                try: # Catch buffer overrun/underrun
                    ident = packet_buff.unpack_varint()
                    self.packet_received(packet_buff, ident)

                except BufferUnderrun:
                    raise ProtocolError("Packet is too short!")

                if packet_buff.length() > 0:
                    raise ProtocolError("Packet is too long!")

            except ProtocolError as e:
                self.protocol_error(e)
                break

            # We've read a complete packet, so reset the inactivity timeout
            self.connection_timer.reset()

    def packet_received(self, buff, ident):
        """ Dispatches packet to registered handler """

        self.log_packet("<<", ident)

        handler = self.packet_handlers.get((self.protocol_mode, ident), None)
        if handler:
            return getattr(self, handler)(buff)
        else:
            return self.packet_unhandled(buff, ident)

    def packet_unhandled(self, buff, ident):
        """Called when a packet has no registered handler"""

        buff.discard()

    def send_packet(self, ident, data=""):
        """ Sends a packet """

        self.log_packet(">>", ident)

        # Prepend length and ident
        data = Buffer.pack_varint(ident) + data
        data = Buffer.pack_varint(len(data)) + data

        # Encrypt
        data = self.cipher.encrypt(data)

        # Send
        self.transport.write(data)

class Factory(protocol.Factory, object):
    protocol = Protocol
    log_level = logging.INFO
    connection_timeout = 30
    auth_timeout = 30

    def buildProtocol(self, addr):
        return self.protocol(self, addr)

    def run(self):
        reactor.run()

    def stop(self):
        reactor.stop()