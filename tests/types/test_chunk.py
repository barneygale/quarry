import os.path

from quarry.types.buffer import Buffer
from quarry.types.chunk import BlockArray

chunk_path = os.path.join(os.path.dirname(__file__), "chunk.bin")


def test_chunk_pack_unpack():
    with open(chunk_path, "rb") as fd:
        chunk_data_before = fd.read()

    buff = Buffer(chunk_data_before)
    blocks, block_lights, sky_lights = buff.unpack_chunk_section()
    chunk_data_after = Buffer.pack_chunk_section(blocks, block_lights, sky_lights)

    assert len(buff) == 0
    assert blocks      [1400:1410] == [32, 32, 32, 288, 275, 288, 288, 497, 497, 0]
    assert block_lights[1400:1410] == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert sky_lights  [1400:1410] == [0, 0, 0, 13, 0, 12, 11, 10, 14, 15]
    assert chunk_data_before == chunk_data_after

def test_chunk_internals():
    blocks = BlockArray([0]*4096, 4, [0])

    # Accumulate blocks
    added = []
    for i in range(300):
        blocks[i] = i
        added.append(i)

        assert blocks[:i+1] == added

        if i < 256:
            assert len(blocks.palette) == i + 1
            if i < 16:
                assert blocks.bits == 4
            elif i < 32:
                assert blocks.bits == 5
            elif i < 64:
                assert blocks.bits == 6
            elif i < 128:
                assert blocks.bits == 7
            else:
                assert blocks.bits == 8
        else:
            assert blocks.palette is None
            assert blocks.bits == 13

    # Zero the first 100 blocks
    for i in range(100):
        blocks[i] = 0
    blocks.repack()
    assert len(blocks.palette) == 201
    assert blocks.bits == 8

    # Zero blocks 100-199
    for i in range(100, 200):
        blocks[i] = 0
    blocks.repack()
    assert len(blocks.palette) == 101
    assert blocks.bits == 7

    # Zero blocks 205 - 300
    for i in range (205, 300):
        blocks[i] = 0
    blocks.repack()
    assert len(blocks.palette) == 6
    assert blocks.bits == 4

    # Check value
    for i in range(4096):
        if 200 <= i < 205:
            assert blocks[i] == i
        else:
            assert blocks[i] == 0
