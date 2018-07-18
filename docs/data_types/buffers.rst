Buffers
=======

.. module:: quarry.types.buffer

Quarry implements Minecraft's data types by way of the :class:`Buffer` class.

Unpacking
---------

When quarry reads a packet, it stores its payload in a buffer object
and passes the buffer to a packet handler. The packet handler then unpacks
the payload, which usually made up of multiple fields of differing types.
Quarry supports the following methods for working with a buffer:

.. autoclass:: Buffer
    :members: block_map, discard, read, hexdump, unpack, unpack_array,
        unpack_optional, unpack_varint, unpack_packet, unpack_string,
        unpack_json, unpack_chat, unpack_uuid, unpack_position, unpack_block,
        unpack_slot, unpack_nbt, unpack_chunk_section, unpack_entity_metadata,
        unpack_commands, unpack_particle

Packing
-------

Buffers also provide a number of static methods that pack data into
a byte string. A reference to the buffer class is available from
:class:`~quarry.net.protocol.Protocol` objects as ``self.buff_type``.

.. automethod:: Buffer.pack
.. automethod:: Buffer.pack_array
.. automethod:: Buffer.pack_optional
.. automethod:: Buffer.pack_varint
.. automethod:: Buffer.pack_packet
.. automethod:: Buffer.pack_string
.. automethod:: Buffer.pack_json
.. automethod:: Buffer.pack_chat
.. automethod:: Buffer.pack_uuid
.. automethod:: Buffer.pack_position
.. automethod:: Buffer.pack_block
.. automethod:: Buffer.pack_slot
.. automethod:: Buffer.pack_nbt
.. automethod:: Buffer.pack_chunk_section
.. automethod:: Buffer.pack_entity_metadata
.. automethod:: Buffer.pack_commands
.. automethod:: Buffer.pack_particle

Protocol Versions
-----------------

Some data types vary between Minecraft versions. Quarry automatically sets the
``buff_type`` attribute of ``Protocol`` instance to an appropriate buffer
class when the protocol version becomes known.

Minecraft 1.7
~~~~~~~~~~~~~

Support for Minecraft 1.7+ is implemented in the :class:`Buffer1_7` class.

Minecraft 1.9
~~~~~~~~~~~~~

Support for Minecraft 1.9+ is implemented in the :class:`Buffer1_9` class.

Changes from 1.7:

- ``pack_chunk_section()`` and ``unpack_chunk_section()`` added.
- ``pack_entity_metadata()`` and ``unpack_entity_metadata()`` modified.

Minecraft 1.13
~~~~~~~~~~~~~~

Support for Minecraft 1.13+ is implemented in the :class:`Buffer1_13` class.

Changes from 1.9:

- ``pack_commands()`` and ``unpack_commands()`` added.
- ``pack_particle()`` and ``unpack_particle()`` added.
- ``pack_chunk_section_palette()`` and ``unpack_chunk_section_palette()``
  modified.
- ``pack_slot()`` and ``unpack_slot()`` modified.
- ``pack_entity_metadata()`` and ``unpack_entity_metadata()`` modified.