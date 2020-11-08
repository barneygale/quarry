import os.path

import bitstring

from quarry.types.buffer import Buffer1_13_2, Buffer1_14
from quarry.types.chunk import PackedArray, BlockArray
from quarry.types.registry import OpaqueRegistry, BitShiftRegistry
from quarry.types.nbt import TagCompound

TagCompound.preserve_order = True # for testing purposes.

root_path = os.path.dirname(__file__)
chunk_path = os.path.join(root_path, "chunk.bin")
packet_path = os.path.join(root_path, "packet.bin")


def test_wikivg_example():
    # Example from https://wiki.vg/Chunk_Format#Example
    data = bitstring.BitArray(length=13*4096)
    data[0:64]   = '0b0000000000100000100001100011000101001000010000011000100001000001'
    data[64:128] = '0b0000000100000001100010100111001001100000111101101000110010000111'
    data = data.bytes

    blocks = BlockArray.from_bytes(data, 5, OpaqueRegistry(13), [])
    assert blocks[:24] == [
        1, 2, 2, 3, 4, 4, 5, 6, 6, 4, 8, 0, 7,
        4, 3, 13, 15, 16, 9, 14, 10, 12, 0, 2]


# See https://github.com/barneygale/quarry/issues/66
# See https://github.com/barneygale/quarry/issues/100
def test_packet_pack_unpack():
    bt = Buffer1_14

    with open(packet_path, "rb") as f:
        packet_data_before = f.read()

    # Unpack
    buff = bt(packet_data_before)
    bitmask = buff.unpack_varint()
    heightmap = buff.unpack_nbt()
    biomes = [buff.unpack_varint() for _ in range(buff.unpack_varint())]
    sections_length = buff.unpack_varint()
    sections = buff.unpack_chunk(bitmask)
    block_entities = [buff.unpack_nbt() for _ in range(buff.unpack_varint())]

    # Basics
    assert len(buff) == 0
    assert bitmask == 0b11111

    # Height data
    motion_blocking = heightmap.body.value['MOTION_BLOCKING'].value
    motion_blocking.value_width = 9
    motion_blocking.length = 256
    assert motion_blocking[0] == 68
    assert motion_blocking[255] == 73

    # Block data
    blocks = sections[0][0]
    assert blocks[::512] == [33, 33, 10, 10, 1, 1, 0, 2]

    # Biomes
    assert biomes[0] == 29

    # Block entities
    assert len(block_entities) == 0

    sections_data_after = bt.pack_chunk(sections)

    packet_data_after = \
        bt.pack_chunk_bitmask(sections) + \
        bt.pack_nbt(heightmap) + \
        bt.pack_varint(len(biomes)) + \
        b"".join(bt.pack_varint(biome) for biome in biomes) + \
        bt.pack_varint(len(sections_data_after)) + \
        sections_data_after + \
        bt.pack_varint(len(block_entities)) + \
        b"".join(bt.pack_nbt(tag) for tag in block_entities)
    assert packet_data_before == packet_data_after

def test_chunk_internals():
    blocks = BlockArray.empty(OpaqueRegistry(13))
    storage = blocks.storage

    # Accumulate blocks
    added = []
    for i in range(300):
        blocks[i] = i
        added.append(i)

        assert blocks[:i+1] == added

        if i < 256:
            assert len(blocks.palette) == i + 1
            if i < 16:
                assert storage.value_width == 4
            elif i < 32:
                assert storage.value_width == 5
            elif i < 64:
                assert storage.value_width == 6
            elif i < 128:
                assert storage.value_width == 7
            else:
                assert storage.value_width == 8
        else:
            assert blocks.palette == []
            assert storage.value_width == 13

    # Zero the first 100 blocks
    for i in range(100):
        blocks[i] = 0
    blocks.repack()
    assert len(blocks.palette) == 201
    assert storage.value_width == 8

    # Zero blocks 100-199
    for i in range(100, 200):
        blocks[i] = 0
    blocks.repack()
    assert len(blocks.palette) == 101
    assert storage.value_width == 7

    # Zero blocks 205 - 300
    for i in range (205, 300):
        blocks[i] = 0
    blocks.repack()
    assert len(blocks.palette) == 6
    assert storage.value_width == 4

    # Check value
    for i in range(4096):
        if 200 <= i < 205:
            assert blocks[i] == i
        else:
            assert blocks[i] == 0
