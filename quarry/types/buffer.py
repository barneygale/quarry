import struct
import json

from quarry.types.uuid import UUID
from quarry.types.chunk import BlockArray, LightArray

# Python 3 compat
try:
    basestring
except NameError:
    basestring = str
try:
    xrange
except NameError:
    xrange = range


class BufferUnderrun(Exception):
    pass


class Buffer(object):
    buff = b""
    pos = 0

    def __init__(self, data=None):
        if data:
            self.buff = data

    def __len__(self):
        return len(self.buff) - self.pos

    def add(self, data):
        """
        Add some bytes to the end of the buffer.
        """

        self.buff += data

    def save(self):
        """
        Saves the buffer contents.
        """

        self.buff = self.buff[self.pos:]
        self.pos = 0

    def restore(self):
        """
        Restores the buffer contents to its state when :meth:`save` was last
        called.
        """

        self.pos = 0

    def discard(self):
        """
        Discards the entire buffer contents.
        """

        self.pos = len(self.buff)

    def read(self, length=None):
        """
        Read *length* bytes from the beginning of the buffer, or all bytes if
        *length* is ``None``
        """

        if length is None:
            data = self.buff[self.pos:]
            self.pos = len(self.buff)
        else:
            if self.pos + length > len(self.buff):
                raise BufferUnderrun()

            data = self.buff[self.pos:self.pos+length]
            self.pos += length

        return data

    def unpack(self, fmt):
        """
        Unpack a struct. The format accepted is the same as for
        ``struct.unpack()``.
        """

        fmt = ">"+fmt
        length = struct.calcsize(fmt)
        fields = struct.unpack(fmt, self.read(length))
        if len(fields) == 1:
            fields = fields[0]
        return fields

    def unpack_string(self):
        """
        Unpack a Minecraft string (varint-prefixed utf8).
        """

        length = self.unpack_varint(max_bits=16)
        text = self.read(length).decode("utf-8")
        return text

    def unpack_json(self):
        """
        Unpack a Minecraft string and interpret it as JSON.
        """

        obj = json.loads(self.unpack_string())
        return obj

    def unpack_chat(self):
        """
        Unpack a Minecraft chat message.
        """
        from quarry.types import chat
        return chat.Message.from_buff(self)

    def unpack_varint(self, max_bits=32, signed=False):
        """
        Unpacks a varint.
        """

        number = 0
        for i in range(5):
            b = self.unpack("B")
            number |= (b & 0x7F) << 7*i
            if not b & 0x80:
                break

        if number & (1<<31):
            number -= 1<<32
            if not signed:
                raise ValueError("varint cannot be negative: %d" % number)

        number_min = -1 << (max_bits - 1)
        number_max = +1 << (max_bits - 1)
        if not (number_min <= number < number_max):
            raise ValueError("varint does not fit in range: %d <= %d < %d"
                             % (number_min, number, number_max))

        return number

    def unpack_uuid(self):
        """
        Unpacks a UUID.
        """

        return UUID.from_bytes(self.read(16))

    def unpack_position(self):
        """
        Unpacks a position.
        """

        def unpack_twos_comp(bits, number):
            if (number & (1 << (bits - 1))) != 0:
                number = number - (1 << bits)
            return number

        number = self.unpack('Q')
        x = unpack_twos_comp(26, (number >> 38))
        y = unpack_twos_comp(12, (number >> 26 & 0xFFF))
        z = unpack_twos_comp(26, (number & 0x3FFFFFF))
        return x, y, z

    def unpack_slot(self):
        """
        Unpacks a slot.
        """

        slot = {}
        slot['id'] = self.unpack('h')
        if slot['id'] != -1:
            slot['count'] = self.unpack('b')
            slot['damage'] = self.unpack('h')
            slot['tag'] = self.unpack_nbt()

        return slot

    def unpack_nbt(self):
        """
        Unpacks NBT tag(s).
        """

        from quarry.types import nbt
        return nbt.TagRoot.from_buff(self)

    def unpack_chunk_section(self, overworld=True):
        """
        Unpacks a chunk section. Returns a 3-tuple of
        ``(blocks, block_lights, sky_lights)``, where *sky_lights* is ``None``
        when *overworld* is ``False``. The returned values are sequences of
        length 4096 (16x16x16).
        """
        bits = self.unpack('B')
        if bits < 4:   bits = 4
        elif bits > 8: bits = 13

        palette = [self.unpack_varint() for _ in xrange(self.unpack_varint())]
        blocks = BlockArray(self.unpack('Q' * self.unpack_varint()), bits, palette)
        block_lights = LightArray(self.unpack('B' * 2048))
        if overworld:
            sky_lights = LightArray(self.unpack('B' * 2048))
        else:
            sky_lights = None

        return blocks, block_lights, sky_lights


    def unpack_entity_metadata_1_7(self):
        """
        Unpacks entity metadata. Compatible with Minecraft 1.7 and 1.8.
        """
        metadata = []
        while True:
            b = self.unpack('B')
            if b == 127:
                return metadata
            ty, key = b >> 5, b & 0x1F
            if   ty == 0: val = self.unpack('b')
            elif ty == 1: val = self.unpack('h')
            elif ty == 2: val = self.unpack('i')
            elif ty == 3: val = self.unpack('f')
            elif ty == 4: val = self.unpack_string()
            elif ty == 5: val = self.unpack_slot()
            elif ty == 6: val = self.unpack('iii')
            elif ty == 7: val = self.unpack('fff')
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata.append((ty, key, val))

    def unpack_entity_metadata(self):
        """
        Unpacks entity metadata. Compatible with Minecraft 1.9+.
        """
        def unpack_optional(unpacker):
            if self.unpack('?'):
                return unpacker()
            else:
                return None

        metadata = []
        while True:
            key = self.unpack('B')
            if key == 255:
                return metadata
            ty = self.unpack('B')
            if   ty == 0:  val = self.unpack('B')
            elif ty == 1:  val = self.unpack_varint()
            elif ty == 2:  val = self.unpack('f')
            elif ty == 3:  val = self.unpack_string()
            elif ty == 4:  val = self.unpack_chat()
            elif ty == 5:  val = self.unpack_slot()
            elif ty == 6:  val = self.unpack('?')
            elif ty == 7:  val = self.unpack('fff')
            elif ty == 8:  val = self.unpack_position()
            elif ty == 9:  val = unpack_optional(self.unpack_position)
            elif ty == 10: val = self.unpack_varint()
            elif ty == 11: val = unpack_optional(self.unpack_uuid)
            elif ty == 12: val = self.unpack_varint()
            elif ty == 13: val = self.unpack_nbt()
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata.append((ty, key, val))


    @classmethod
    def pack(cls, fmt, *fields):
        """
        Pack *fields* into a struct. The format accepted is the same as for
        ``struct.pack()``.
        """

        return struct.pack(">"+fmt, *fields)

    @classmethod
    def pack_string(cls, text):
        """
        Pack a Minecraft string (varint-prefixed utf8).
        """

        text = text.encode("utf-8")
        return cls.pack_varint(len(text), max_bits=16) + text

    @classmethod
    def pack_json(cls, obj):
        """
        Serialize an object to JSON and pack it to a Minecraft string.
        """

        return cls.pack_string(json.dumps(obj))

    @classmethod
    def pack_chat(cls, message):
        """
        Pack a Minecraft chat message.
        """
        from quarry.types import chat
        if not isinstance(message, chat.Message):
            message = chat.Message.from_string(message)
        return message.to_bytes()

    @classmethod
    def pack_varint(cls, number, max_bits=32, signed=False):
        """
        Packs a varint.
        """

        number_min = -1 << (max_bits - 1)
        number_max = +1 << (max_bits - 1)
        if not (number_min <= number < number_max):
            raise ValueError("varint does not fit in range: %d <= %d < %d"
                             % (number_min, number, number_max))

        if number < 0:
            if signed:
                number += 1<<32
            else:
                raise ValueError("varint cannot be negative: %d" % number)

        out = b""
        for i in range(5):
            b = number & 0x7F
            number >>= 7
            out += cls.pack("B", b | (0x80 if number > 0 else 0))
            if number == 0:
                break
        return out

    @classmethod
    def pack_uuid(cls, uuid):
        """
        Packs a UUID.
        """

        return uuid.to_bytes()

    @classmethod
    def pack_position(cls, x, y, z):
        """
        Packs a Position.
        """

        def pack_twos_comp(bits, number):
            if number < 0:
                number = number + (1 << bits)
            return number

        return cls.pack('Q', sum((
            pack_twos_comp(26, x) << 38,
            pack_twos_comp(12, y) << 26,
            pack_twos_comp(26, z))))

    @classmethod
    def pack_slot(cls, id=-1, count=1, damage=0, tag=None):
        """
        Packs a slot.
        """

        if id == -1:
            return cls.pack('h', id)

        return cls.pack('hbh', id, count, damage) + cls.pack_nbt(tag)

    @classmethod
    def pack_nbt(cls, tag=None):
        """
        Packs an NBT tag
        """

        if tag is None:
            # slower but more obvious:
            #   from quarry.types import nbt
            #   tag = nbt.TagRoot({})
            return b"\x00"

        return tag.to_bytes()

    @classmethod
    def pack_chunk_section(cls, blocks, block_lights, sky_lights=None):
        """
        Packs a chunk section. The supplied arguments should be instances of
        ``BlockArray`` and ``LightArray`` from ``quarry.types.chunk``.
        """
        out = Buffer.pack('B', blocks.bits)

        if blocks.palette is None:
            out += Buffer.pack_varint(0)
        else:
            out += Buffer.pack_varint(len(blocks.palette))
            out += b"".join(Buffer.pack_varint(x) for x in blocks.palette)

        out += Buffer.pack_varint(len(blocks.data))
        out += Buffer.pack('Q' * len(blocks.data), *blocks.data)
        out += Buffer.pack('B' * 2048, *block_lights.data)
        if sky_lights:
            out += Buffer.pack('B' * 2048, *sky_lights.data)

        return out

    @classmethod
    def pack_entity_metadata_1_7(cls, metadata):
        """
        Packs entity metadata. Compatible with Minecraft 1.7 and 1.8.
        """
        out = b""
        for ty, key, val in metadata:
            out += cls.pack('B', ty << 5 | key)
            if   ty == 0: out += cls.pack('b', val)
            elif ty == 1: out += cls.pack('h', val)
            elif ty == 2: out += cls.pack('i', val)
            elif ty == 3: out += cls.pack('f', val)
            elif ty == 4: out += cls.pack_string(val)
            elif ty == 5: out += cls.pack_slot(**val)
            elif ty == 6: out += cls.pack('iii', *val)
            elif ty == 7: out += cls.pack('fff', *val)
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
        out += cls.pack('B', 127)
        return out

    @classmethod
    def pack_entity_metadata(cls, metadata):
        """
        Packs entity metadata. Compatible with Minecraft 1.9+.
        """
        def pack_optional(packer, *val):
            if val is None:
                return cls.pack('?', False)
            else:
                return cls.pack('?', True) + packer(*val)

        out = b""
        for ty, key, val in metadata:
            out += cls.pack('BB', key, ty)
            if   ty == 0:  out += cls.pack('B', val)
            elif ty == 1:  out += cls.pack_varint(val)
            elif ty == 2:  out += cls.pack('f', val)
            elif ty == 3:  out += cls.pack_string(val)
            elif ty == 4:  out += cls.pack_chat(val)
            elif ty == 5:  out += cls.pack_slot(**val)
            elif ty == 6:  out += cls.pack('?', val)
            elif ty == 7:  out += cls.pack('fff', *val)
            elif ty == 8:  out += cls.pack_position(*val)
            elif ty == 9:  out += pack_optional(cls.pack_position, *val)
            elif ty == 10: out += cls.pack_varint(val)
            elif ty == 11: out += pack_optional(cls.pack_uuid, val)
            elif ty == 12: out += cls.pack_varint(val)
            elif ty == 13: out += cls.pack_nbt(val)
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
        out += cls.pack('B', 255)
        return out
