Blocks and Chunks
=================

.. currentmodule:: quarry.types.chunk

Minecraft uses tightly-packed arrays to store data like light levels,
heightmaps and block data. Quarry can read and write these formats in both
`Chunk Data`_  packets and ``.mca`` files. Two classes are available for
working with this data:

.. autoclass:: PackedArray
    :members:

.. autoclass:: BlockArray
    :members:


Packets
-------

On the client side, you can unpack a `Chunk Data`_ packet as follows::

    def packet_chunk_data(self, buff):
        x, z, full = buff.unpack('ii?')
        bitmask = buff.unpack_varint()
        heightmap = buff.unpack_nbt()  # added in 1.14
        biomes = [buff.unpack_varint() for _ in range(buff.unpack_varint())]  # changed in 1.16
        sections_length = buff.unpack_varint()
        sections = buff.unpack_chunk(bitmask)
        block_entities = [buff.unpack_nbt() for _ in range(buff.unpack_varint())]

On the server side::

    def send_chunk(self, x, z, full, heightmap, sections, biomes, block_entities):
        sections_data = self.bt.pack_chunk(sections)
        self.send_packet(
            'chunk_data',
            self.bt.pack('ii?', x, z, full),
            self.bt.pack_chunk_bitmask(sections),
            self.bt.pack_nbt(heightmap),  # added in 1.14
            self.bt.pack_varint(len(biomes)),  # changed in 1.16
            b''.join(self.bt.pack_varint(biome) for biome in biomes),  # changed in 1.16
            self.bt.pack_varint(len(sections_data)),
            sections_data,
            self.bt.pack_varint(len(block_entities)),
            b''.join(self.bt.pack_nbt(entity) for entity in block_entities))

The variables used in these examples are as follows:


.. list-table::
    :header-rows: 1

    - * Variable
      * Value type
    - * ``x``
      * ``int``
    - * ``z``
      * ``int``
    - * ``full``
      * ``bool``
    - * ``bitmask``
      * ``int``
    - * ``heightmap``
      * ``TagRoot[TagCompound[TagLongArray[PackedArray]]]``
    - * ``sections``
      * ``List[Optional[BlockArray]]``
    - * ``biomes``
      * ``List[int]``
    - * ``block_entities``
      * ``List[TagRoot]``



Regions
-------

Quarry can load and save data from the ``.mca`` format via the
:class:`~quarry.types.nbt.RegionFile` class. NBT tags such as ``"BlockStates"``,
``"BlockLight"``, ``"SkyLight"`` and heightmaps such as ``"MOTION_BLOCKING"``
make their values available as :class:`PackedArray` objects.

Use :meth:`BlockArray.from_nbt` with a
:class:`~quarry.types.registry.LookupRegistry` to create a block array backed
by NBT data. Modifications to the block array will automatically be reflected
in the NBT data, and vice versa.

Putting these pieces together, the following function could be used to set a
block in an existing region file::

    import os.path

    from quarry.types.nbt import RegionFile
    from quarry.types.registry import LookupRegistry
    from quarry.types.chunk import BlockArray


    def set_block(server_path, x, y, z, block):
        rx, x = divmod(x, 512)
        rz, z = divmod(z, 512)
        cx, x = divmod(x, 16)
        cy, y = divmod(y, 16)
        cz, z = divmod(z, 16)

        jar_path = os.path.join(server_path, "minecraft_server.jar")
        region_path = os.path.join(server_path, "world", "region", "r.%d.%d.mca" % (rx, rz))

        registry = LookupRegistry.from_jar(jar_path)
        with RegionFile(region_path) as region:
            chunk, section = region.load_chunk_section(cx, cy, cz)
            blocks = BlockArray.from_nbt(section, registry)
            blocks[256 * y + 16 * z + x] = block
            region.save_chunk(chunk)


    set_block("/path/to/server", 10, 80, 40, {'name': 'minecraft:bedrock'})

.. _Chunk Data: http://wiki.vg/Protocol#Chunk_Data
