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
    data[0:64]   = '0b0000000100000000000110001000000011000000000001100000000000100000'
    data[64:128] = '0b0000001000000000110100000000011010000000000001001100000000100000'
    data = data.bytes

    blocks = BlockArray.from_bytes(data, [], BitShiftRegistry(13), 10)
    assert blocks[0] == (2, 0)  # grass
    assert blocks[1] == (3, 0)  # dirt
    assert blocks[2] == (3, 0)  # dirt
    assert blocks[3] == (3, 1)  # coarse dirt
    assert blocks[4] == (1, 0)  # stone
    assert blocks[5] == (1, 0)  # stone
    assert blocks[6] == (1, 3)  # diorite
    assert blocks[7] == (13, 0) # gravel
    assert blocks[8] == (13, 0) # gravel
    assert blocks[9] == (1, 0)  # stone


def test_chunk_pack_unpack():
    bt = Buffer1_13_2

    with open(chunk_path, "rb") as fd:
        chunk_data_before = fd.read()

    # Unpack
    buff = bt(chunk_data_before)
    blocks, block_lights, sky_lights = buff.unpack_chunk_section()

    assert len(buff) == 0
    assert blocks      [1400:1410] == [32, 32, 32, 288, 275, 288, 288, 497, 497, 0]
    assert block_lights[1400:1410] == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert sky_lights  [1400:1410] == [0, 0, 0, 13, 0, 12, 11, 10, 14, 15]

    # Pack
    chunk_data_after = bt.pack_chunk_section(blocks, block_lights, sky_lights)
    assert chunk_data_before == chunk_data_after


# See https://github.com/barneygale/quarry/issues/66
def test_packet_pack_unpack():
    bt = Buffer1_14

    with open(packet_path, "rb") as f:
        packet_data_before = f.read()

    # Unpack
    buff = bt(packet_data_before)
    bitmask = buff.unpack_varint()
    heightmap = buff.unpack_nbt()
    motion_blocking = heightmap.body.value['MOTION_BLOCKING'].value
    sections_length = buff.unpack_varint()
    sections = buff.unpack_chunk(bitmask)
    biomes = buff.unpack('I' * 256)
    block_entities = [buff.unpack_nbt() for _ in range(buff.unpack_varint())]
    assert len(buff) == 0
    assert bitmask == 0b1111
    assert motion_blocking[0] == 63
    assert motion_blocking[255] == 64
    assert sections[0][0][0] == 33
    assert biomes[0] == 16
    assert len(block_entities) == 0

    sections_data_after = bt.pack_chunk(sections) + bt.pack_array('I', biomes)

    packet_data_after = \
        bt.pack_chunk_bitmask(sections) + \
        bt.pack_nbt(heightmap) + \
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
