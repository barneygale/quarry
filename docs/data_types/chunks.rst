Blocks, Chunks and Regions
==========================

Blocks
------

.. currentmodule:: quarry.types.buffer

Quarry can be told to encode/decode block and item information by setting the
:attr:`Buffer.block_map` attribute on the in-use buffer. This can be set
directly or by deriving a subclass and customizing
:meth:`Factory.get_buff_type()`. The block map affects the following methods:

- :meth:`~Buffer.unpack_slot()` and :meth:`~Buffer.pack_slot()`
- :meth:`~Buffer.unpack_block()` and :meth:`~Buffer.pack_block()`
- :meth:`~Buffer.unpack_entity_metadata()` and
  :meth:`~Buffer.pack_entity_metadata()`
- :meth:`~Buffer.unpack_chunk_section()` and :meth:`~Buffer.pack_chunk_section()`

.. module:: quarry.types.block

All block map objects have the following methods:

.. automethod:: BlockMap.encode_block
.. automethod:: BlockMap.decode_block
.. automethod:: BlockMap.encode_item
.. automethod:: BlockMap.decode_item

Quarry supports the following block map types:

.. autoclass:: OpaqueBlockMap
.. autoclass:: BitShiftBlockMap
.. autoclass:: LookupBlockMap
    :members: from_jar, from_json


Chunks
------

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

Regions
-------

Quarry can load and save block and light data from the ``.mca`` format used in
Minecraft 1.13+. This requires the use of a
:class:`~quarry.types.nbt.RegionFile`.

Use :meth:`BlockArray.from_nbt` with a
:class:`~quarry.types.block.LookupBlockMap` to create a block array backed by
NBT data. Modifications to the block array will automatically be reflected in
the NBT data, and vice versa. Use :meth:`LightArray.from_nbt()` for equivalent
functionality for light arrays.

Putting these pieces together, the following function could be used to set a
block in an existing region file::

    import os.path

    from quarry.types.nbt import RegionFile
    from quarry.types.block import LookupBlockMap
    from quarry.types.chunk import BlockArray


    def set_block(server_path, x, y, z, block):
        rx, x = divmod(x, 512)
        rz, z = divmod(z, 512)
        cx, x = divmod(x, 16)
        cy, y = divmod(y, 16)
        cz, z = divmod(z, 16)

        jar_path = os.path.join(server_path, "minecraft_server.jar")
        region_path = os.path.join(server_path, "world", "region", "r.%d.%d.mca" % (rx, rz))

        block_map = LookupBlockMap.from_jar(jar_path)
        with RegionFile(region_path) as region:
            chunk = region.load_chunk(cx, cz)
            for section in chunk.body.value["Level"].value["Sections"].value:
                if section.value["Y"].value == cy:
                    blocks = BlockArray.from_nbt(section, block_map)
                    blocks[256 * y + 16 * z + x] = block
                    region.save_chunk(chunk)
                    break
            else:
                raise Exception("Chunk section not found")


    set_block("/path/to/server", 10, 80, 40, {'name': 'minecraft:bedrock'})