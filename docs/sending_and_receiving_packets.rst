Sending and Receiving Packets
=============================

Receiving a Packet
------------------

To receive a packet, implement a method in your subclass of
:class:`~quarry.net.client.ClientProtocol` or
:class:`~quarry.net.server.ServerProtocol` with a name like
``packet_<packet name>``::

    def packet_update_health(self, buff):
        health = buff.unpack('f')
        food = buff.unpack_varint()
        saturation = buff.unpack('f')

You are passed a :class:`~quarry.utils.buffer.Buffer` instance, which contains
the payload of the packet. If you hook a packet, you should ensure you read the
entire payload.

Sending a Packet
----------------

Call :meth:`~quarry.net.protocol.Protocol.send_packet` to send a packet::

    def packet_keep_alive(self, buff):
        # Read the keep alive ID
        identifier = buff.unpack_varint()
        print(identifier)

        # Send a keep alive back
        self.send_packet("keep_alive", self.buff_type.pack_varint(identifier))


To construct the payload, call static methods on :class:`Buffer`. A reference
to this class is available as ``self.buff_type``.

Buffer Methods
--------------

.. autoclass:: quarry.utils.buffer.Buffer
    :members: