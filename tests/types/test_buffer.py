from collections import OrderedDict

import pytest

from quarry.types.buffer import Buffer, BufferUnderrun
from quarry.types.chat import Message
from quarry.types.nbt import *
from quarry.types.uuid import UUID

TagCompound.preserve_order = True # for testing purposes.

pack_unpack_vectors = [
    ("??",   b"\x00\x01", (False, True)),
    ("bbbb", b"\x00\x7F\x80\xFF", (0, 127, -128, -1)),
    ("BBBB", b"\x00\x7F\x80\xFF", (0, 127, 128, 255)),
    ("hhhh", b"\x00\x00\x7F\xFF\x80\x00\xFF\xFF", (0, 32767, -32768, -1)),
    ("HHHH", b"\x00\x00\x7F\xFF\x80\x00\xFF\xFF", (0, 32767, 32768, 65535)),
    ("iiii", b"\x00\x00\x00\x00\x7F\xFF\xFF\xFF"
             b"\x80\x00\x00\x00\xFF\xFF\xFF\xFF", (0, 2147483647,
                                                   -2147483648, -1)),
    ("qqqq", b"\x00\x00\x00\x00\x00\x00\x00\x00"
             b"\x7F\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
             b"\x80\x00\x00\x00\x00\x00\x00\x00"
             b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF", (0, 9223372036854775807,
                                                   -9223372036854775808, -1)),
    ("f",    b"\x40\x00\x00\x00", 2),
    ("d",    b"\x40\x00\x00\x00\x00\x00\x00\x00", 2)
]

uuid_vector = b"\xcb\x3f\x5c\x3d\x0c\x13\x47\x68"\
              b"\x9b\x3c\x43\x3e\x37\x28\x75\x97"

varint_vectors = [
    (1, b"\x01"),
    (127, b"\x7f"),
    (300, b"\xAC\x02"),
    (100000, b"\xA0\x8D\x06"),
    (16909060, b"\x84\x86\x88\x08"),
    (-1, b"\xFF\xFF\xFF\xFF\x0F"),
    (2147483647, b"\xFF\xFF\xFF\xFF\x07"),
    (-2147483648, b"\x80\x80\x80\x80\x08"),
]
slot_vectors = [
    # Empty slot
    ({'item': None}, b'\x00'),

    # 20 stone blocks
    ({'item': 276, 'count': 20, 'tag': TagRoot({})},

        b'\x01'     # Present
        b'\x94\x02' # ID
        b'\x14'     # Count
        b'\x00'),   # NBT

    # Sharpness 4 diamond sword
    ({'item': 276, 'count': 1, 'tag': TagRoot({'': TagCompound({
        'ench': TagList([
             TagCompound(OrderedDict((
                 ('id', TagShort(16)),
                 ('lvl', TagShort(4)))))])})})},  # hmm

        b'\x01'     # Present
        b'\x94\x02' # ID
        b'\x01'     # Count
        b'\x0A\x00\x00\x09\x00\x04ench\n\x00\x00\x00\x01' # NBT container start
        b'\x02\x00\x02id\x00\x10'                         # Enchantment type
        b'\x02\x00\x03lvl\x00\x04'                        # Enchantment level
        b'\x00\x00'),                                     # NBT container end
]
entity_metadata_vectors = [
    (OrderedDict((
        ((0, 0), 0),
        ((1, 1), 1),
        ((2, 2), 2.0),
        ((3, 3), 'three'),
        ((4, 4), Message({'text': 'four'})),
        ((5, 5), Message({'text': 'five'})),
        ((6, 6), {'count': 1, 'item': 267, 'tag': TagRoot({})}),
        ((7, 7), True),
        ((8, 8), (8, 8, 8)),
        ((9, 9), (9, 9, 9)),
        ((10, 10), (10, 10, 10)),
        ((11, 11), 'north'),
        ((12, 12), UUID.from_bytes(uuid_vector)),
        ((13, 13), 13),
        ((14, 14), TagRoot({'foo': TagString('bar')})))),

        b'\x00\x00\x00'
        b'\x01\x01\x01'
        b'\x02\x02\x40\x00\x00\x00'
        b'\x03\x03\x05three'
        b'\x04\x04\x10{"text": "four"}'
        b'\x05\x05\x01\x10{"text": "five"}'
        b'\x06\x06\x01\x8b\x02\x01\x00'
        b'\x07\x07\x01'
        b'\x08\x08\x41\x00\x00\x00\x41\x00\x00\x00\x41\x00\x00\x00'
        b'\x09\x09\x00\x00\x02\x40\x00\x00\x90\x09'
        b'\x0a\x0a\x01\x00\x00\x02\x80\x00\x00\xa0\x0a'
        b'\x0b\x0b\x02'
        b'\x0c\x0c\x01' + uuid_vector +
        b'\x0d\x0d\x0d'
        b'\x0e\x0e\x08\x00\x03foo\x00\x03bar'
        b'\xff')
]

def test_add():
    buffer = Buffer()
    buffer.add(b"spam")
    assert len(buffer) == 4
    assert buffer.read() == b"spam"

def test_save_discard_restore():
    buffer = Buffer()
    buffer.add(b"spam")
    buffer.save()
    assert len(buffer) == 4
    buffer.discard()
    assert len(buffer) == 0
    buffer.restore()
    assert len(buffer) == 4

def test_read():
    buffer = Buffer()
    buffer.add(b"spam")
    assert buffer.read(2) == b"sp"
    assert buffer.read(2) == b"am"
    buffer.add(b"eggs")
    assert buffer.read() == b"eggs"
    with pytest.raises(BufferUnderrun):
        buffer.read(1)

def test_unpack():
    buffer = Buffer()
    for fmt, data, values in pack_unpack_vectors:
        buffer.add(data)
        assert buffer.unpack(fmt) == values

def test_unpack_string():
    buffer = Buffer()
    buffer.add(b"\x04spam")
    assert buffer.unpack_string() == "spam"

def test_unpack_json():
    buffer = Buffer()
    buffer.add(b'\x10{"spam": "eggs"}')
    assert buffer.unpack_json() == {"spam": "eggs"}

def test_unpack_chat():
    buffer = Buffer()
    buffer.add(b'\x11["spam", " eggs"]')
    assert buffer.unpack_chat().to_string() == "spam eggs"
    buffer.add(b'\x22{"text": "spam", "extra": " eggs"}')
    assert buffer.unpack_chat().to_string() == "spam eggs"
    buffer.add(b'\x14{"translate": "foo"}')
    assert buffer.unpack_chat().to_string() == "foo"
    buffer.add(b'\x2E{"translate": "foo", "with": ["spam", "eggs"]}')
    assert buffer.unpack_chat().to_string() == "foo{spam, eggs}"

def test_unpack_varint():
    buffer = Buffer()
    for value, data in varint_vectors:
        buffer.add(data)
        assert buffer.unpack_varint() == value
        assert len(buffer) == 0

def test_unpack_uuid():
    buffer = Buffer()
    buffer.add(uuid_vector)
    assert buffer.unpack_uuid().to_bytes() == uuid_vector

def test_unpack_slot():
    buffer = Buffer()
    for value, data in slot_vectors:
        buffer.add(data)
        assert buffer.unpack_slot() == value
        assert len(buffer) == 0

def test_unpack_entity_metadata():
    buffer = Buffer()
    for value, data in entity_metadata_vectors:
        buffer.add(data)
        assert buffer.unpack_entity_metadata() == value
        assert len(buffer) == 0

def test_pack():
    for fmt, data, values in pack_unpack_vectors:
        if not isinstance(values, tuple):
            values = (values,)
        assert Buffer.pack(fmt, *values) == data

def test_pack_string():
    assert Buffer.pack_string("spam") == b"\x04spam"

def test_pack_json():
    assert Buffer.pack_json({"spam": "eggs"}) == b'\x10{"spam": "eggs"}'

def test_pack_chat():
    assert Buffer.pack_chat("spam") == b'\x10{"text": "spam"}'

def test_pack_varint():
    for value, data in varint_vectors:
        assert Buffer.pack_varint(value) == data

def test_pack_uuid():
    assert Buffer.pack_uuid(UUID.from_bytes(uuid_vector)) == uuid_vector

def test_pack_slot():
    for value, data in slot_vectors:
        assert Buffer.pack_slot(**value) == data

def test_pack_entity_metadata():
    for value, data in entity_metadata_vectors:
        assert Buffer.pack_entity_metadata(value) == data