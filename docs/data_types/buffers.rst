Buffers
=======

.. module:: quarry.types.buffer

Quarry implements Minecraft's data types by way of the :class:`Buffer` class.

Unpacking
---------

When quarry reads a packet, it stores its payload in a :class:`Buffer` object
and passes the buffer to a packet handler. The packet handler then unpacks
the payload, which usually made up of multiple fields of differing types.
Quarry supports the following methods for working with a buffer:

.. autoclass:: Buffer
    :members: discard, read, unpack, unpack_string, unpack_json, unpack_chat,
        unpack_varint, unpack_uuid, unpack_position, unpack_slot, unpack_nbt,
        unpack_chunk_section, unpack_entity_metadata

Packing
-------

:class:`Buffer` also provides a number of static methods that pack data into
a byte string. A reference to the :class:`Buffer` class is available from
:class:`~quarry.net.protocol.Protocol` objects as ``self.buff_type``.

.. automethod:: Buffer.pack
.. automethod:: Buffer.pack_string
.. automethod:: Buffer.pack_json
.. automethod:: Buffer.pack_chat
.. automethod:: Buffer.pack_varint
.. automethod:: Buffer.pack_uuid
.. automethod:: Buffer.pack_position
.. automethod:: Buffer.pack_slot
.. automethod:: Buffer.pack_nbt
.. automethod:: Buffer.pack_chunk_section
.. automethod:: Buffer.pack_entity_metadata