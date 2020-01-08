Buffers
=======

.. module:: quarry.types.buffer

Quarry implements Minecraft's data types by way of the :class:`Buffer` class.

When quarry reads a packet, it stores its payload in a buffer object
and passes the buffer to a packet handler. The packet handler then unpacks
the payload, which usually made up of multiple fields of differing types. You
can read from the front of the buffer via the :meth:`Buffer.read` method or any
of the ``unpack_*()`` methods listed below

Buffers also provide a number of static methods that pack data into
a byte string. These are named like ``pack_*()``.

When *unpacking* data you work with a buffer *object*, whereas when packing
data you work with a buffer *type*. A reference to the buffer type is available
from :class:`~quarry.net.protocol.Protocol` objects as ``self.buff_type``.


.. autoclass:: Buffer
    :members:
    :inherited-members:

    .. autoattribute:: registry

        An object that encodes/decodes IDs, such as blocks and items.


Protocol Versions
-----------------

Some data types vary between Minecraft versions. Quarry automatically sets the
``buff_type`` attribute of ``Protocol`` instance to an appropriate buffer
class when the protocol version becomes known.

Minecraft 1.7
~~~~~~~~~~~~~

Support for Minecraft 1.7+ is implemented in the ``Buffer1_7`` class.

Minecraft 1.9
~~~~~~~~~~~~~

Support for Minecraft 1.9+ is implemented in the ``Buffer1_9`` class.

Changes from 1.7:

- ``pack_chunk_section()`` and ``unpack_chunk_section()`` added.
- ``pack_entity_metadata()`` and ``unpack_entity_metadata()`` modified.

Minecraft 1.13
~~~~~~~~~~~~~~

Support for Minecraft 1.13+ is implemented in the ``Buffer1_13`` class.

Changes from 1.9:

- ``pack_commands()`` and ``unpack_commands()`` added.
- ``pack_particle()`` and ``unpack_particle()`` added.
- ``pack_recipes()`` and ``unpack_recipes()`` added.
- ``pack_chunk_section_palette()`` and ``unpack_chunk_section_palette()``
  modified.
- ``pack_slot()`` and ``unpack_slot()`` modified.
- ``pack_entity_metadata()`` and ``unpack_entity_metadata()`` modified.

Minecraft 1.13.2
~~~~~~~~~~~~~~~~

Support for Minecraft 1.13.2+ is implemented in the ``Buffer1_13_2``
class.

Changes from 1.13:

- ``pack_slot()`` and ``unpack_slot()`` modified.

Minecraft 1.14
~~~~~~~~~~~~~~

Support for Minecraft 1.14+ is implemented in the ``Buffer1_14`` class.

Changes from 1.13.2:

- ``pack_villager()`` and ``unpack_villager()`` added.
- ``pack_optional_varint()`` and ``unpack_optional_varint()`` added.
- ``pack_pose()`` and ``unpack_pose()`` added.
- ``pack_chunk_section()`` and ``unpack_chunk_section()`` modified.
- ``pack_position()`` and ``unpack_position()`` modified.
- ``pack_entity_metadata()`` and ``unpack_entity_metadata()`` modified.
- ``pack_particle()`` and ``unpack_particle()`` modified.
- ``pack_recipes()`` and ``unpack_recipes()`` modified.
