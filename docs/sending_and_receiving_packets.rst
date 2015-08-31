Sending and Receiving Packets
=============================

Receiving a Packet
------------------

To receive a packet, implement a method in your subclass of
:class:`ClientProtocol` or :class:`ServerProtocol` with a name like
``packet_<packet name>``::

    def packet_update_health(self, buff):
        health = buff.unpack('f')
        food = buff.unpack_varint()
        saturation = buff.unpack('f')

You are passed a :class:`Buffer` instance, which contains the payload of the
packet. If you hook a packet, you should ensure you read the entire payload.

Sending a Packet
----------------

Call :meth:`Protocol.send_packet` to send a packet::

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

.. class:: Buffer

    .. method:: discard(self):

        Discard the entire buffer.

    .. method:: read(self, length=None)

        Read *length* bytes from the buffer, or all bytes if *length* is
        ``None``.

    .. method:: unpack(self, fmt)

        Unpack a struct from the buffer. The format accepted is the same as
        for ``struct.unpack()``.

    .. method:: unpack_string(self)

        Unpack a Minecraft string (varint-prefixed utf8) from the buffer.

    .. method:: unpack_json(self)

        Unpack a Minecraft string and interpret it as JSON.

    .. method:: unpack_chat(self)

        Unpack a Minecraft chat message. Minecraft uses a JSON format to
        send chat messages; this method retrieves a plaintext representation
        with colours and styles stripped.

    .. method:: unpack_varint(self)

        Unpacks a VarInt from the buffer.

    .. method:: unpack_uuid(self)

        Unpacks a UUID from the buffer.

    .. method:: pack(cls, fmt, *data)

        Pack *data* into a struct. The format accepted is the same as for
        ``struct.pack()``.

    .. method:: pack_string(cls, text)

        Pack a Minecraft string (varint-prefixed utf8).

    .. method:: pack_json(cls, obj)

        Dump an object to JSON and pack it to a Minecraft string.

    .. method:: pack_chat(cls, text)

        Pack a Minecraft chat message. This method accepts plaintext; to send
        colours and other formatting use :meth:`pack_json`.

    .. method:: pack_varint(cls, number)

        Packs a VarInt.

    .. method:: pack_uuid(cls, uuid)

        Packs a UUID.