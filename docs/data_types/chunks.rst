Chunks and Blocks
=================

.. module:: quarry.types.chunk

Quarry implements the `Chunk Section`_ data type used in `Chunk Data`_ packets.
This format consists of:

* A tightly-packed array of blocks using either:

  - 4-8 bits per block, with a palette
  - 13 (Minecraft 1.9 - 1.12) or 14 (1.13+) bits per block, without a palette.

* A tightly-packed array of light using 4 bits per block.

.. _Chunk Section: http://wiki.vg/SMP_Map_Format
.. _Chunk Data: http://wiki.vg/Protocol#Chunk_Data

These types are implemented through the :class:`BlockArray` and
:class:`LightArray` classes. Each is a sequence containing exactly 4096 values
(16x16x16) and supporting the usual sequence operations (iteration, get/set
values, etc).

.. currentmodule:: quarry.types.buffer

On the client side, call :meth:`Buffer.unpack_chunk_section()` to retrieve a
tuple of block data, block light and (if *overworld* is ``True``) sky light.

On the server side, call :meth:`Buffer.pack_chunk_section()`, passing in block
data, block light and either sky light or ``None``.

.. currentmodule:: quarry.types.chunk

.. autoclass:: BlockArray
    :undoc-members:
    :members:


.. autoclass:: LightArray
    :undoc-members:
    :members:

Block Maps
----------

.. currentmodule:: quarry.types.buffer

Quarry can be told to encode/decode block and item information by setting the
:attr:`Buffer.block_map` attribute on the in-use buffer. This can be set
directly or by deriving a subclass and customizing
:meth:`Factory.get_buff_type()`. The block map affects the following methods:

- :meth:`~Buffer.unpack_slot()` and :meth:`~Buffer.pack_slot()`
- :meth:`~Buffer.unpack_block()` and :meth:`~Buffer.pack_block()`
- :meth:`~Buffer.unpack_entity_metadata()` and
  :meth:`~Buffer.pack_entity_metadata()`
- :meth:`~Buffer.unpack_chunk_section()`

.. module:: quarry.types.block

Quarry supports the following block map types:

.. autoclass:: OpaqueBlockMap
.. autoclass:: BitShiftBlockMap
.. autoclass:: LookupBlockMap
    :members: from_jar, from_json

All block map objects have the following methods:

.. automethod:: BlockMap.encode_block
.. automethod:: BlockMap.decode_block
.. automethod:: BlockMap.encode_item
.. automethod:: BlockMap.decode_item