import json
import string
import struct
import sys
import zlib

from quarry.types.buffer import BufferUnderrun
from quarry.types.uuid import UUID
from quarry.types.block import OpaqueBlockMap

PY3 = sys.version_info > (3,)

# Python 3 compat
try:
    xrange
except NameError:
    xrange = range


class Buffer1_7(object):
    buff = b""
    pos = 0
    block_map = OpaqueBlockMap(13)

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

    def hexdump(self):
        printable = string.letters + string.digits + string.punctuation
        data = self.buff[self.pos:]
        lines = ['']
        bytes_read = 0
        while len(data) > 0:
            data_line, data = data[:16], data[16:]

            l_hex = []
            l_str = []
            for i, c in enumerate(data_line):
                if PY3:
                    l_hex.append("%02x" % c)
                    c_str = data_line[i:i + 1]
                    l_str.append(
                        c_str if c_str in printable else ".")
                else:
                    l_hex.append("%02x" % ord(c))
                    l_str.append(c if c in printable else ".")

            l_hex.extend(['  '] * (16 - len(l_hex)))
            l_hex.insert(8, '')

            lines.append("%08x  %s  |%s|" % (
                bytes_read,
                " ".join(l_hex),
                "".join(l_str)))

            bytes_read += len(data_line)

        return "\n    ".join(lines + ["%08x" % bytes_read])

    # Basic data types --------------------------------------------------------

    @classmethod
    def pack(cls, fmt, *fields):
        """
        Pack *fields* into a struct. The format accepted is the same as for
        ``struct.pack()``.
        """

        return struct.pack(">"+fmt, *fields)

    def unpack(self, fmt):
        """
        Unpack a struct. The format accepted is the same as for
        ``struct.unpack()``.
        """
        fmt = ">" + fmt
        data = self.read(struct.calcsize(fmt))
        fields = struct.unpack(fmt, data)
        if len(fields) == 1:
            fields = fields[0]
        return fields

    # Array data types --------------------------------------------------------

    @classmethod
    def pack_array(cls, fmt, array):
        """
        Packs *array* into a struct. The format accepted is the same as for
        ``struct.pack()``.
        """
        return struct.pack(">" + fmt * len(array), *array)

    def unpack_array(self, fmt, length):
        """
        Unpack an array struct. The format accepted is the same as for
        ``struct.unpack()``.
        """
        data = self.read(struct.calcsize(">" + fmt) * length)
        return list(struct.unpack(">" + fmt * length, data))

    # Optional ----------------------------------------------------------------

    @classmethod
    def pack_optional(cls, packer, val):
        """
        Packs a boolean indicating whether *val* is None. If not,
        ``packer(val)`` is appended to the returned string.
        """

        if val is None:
            return cls.pack('?', False)
        else:
            return cls.pack('?', True) + packer(val)

    def unpack_optional(self, unpacker):
        """
        Unpacks a boolean. If it's True, return the value of ``unpacker()``.
        Otherwise return None.
        """
        if self.unpack('?'):
            return unpacker()
        else:
            return None

    # Varint ------------------------------------------------------------------

    @classmethod
    def pack_varint(cls, number, max_bits=32):
        """
        Packs a varint.
        """

        number_min = -1 << (max_bits - 1)
        number_max = +1 << (max_bits - 1)
        if not (number_min <= number < number_max):
            raise ValueError("varint does not fit in range: %d <= %d < %d"
                             % (number_min, number, number_max))

        if number < 0:
            number += 1 << 32

        out = b""
        for i in xrange(10):
            b = number & 0x7F
            number >>= 7
            out += cls.pack("B", b | (0x80 if number > 0 else 0))
            if number == 0:
                break
        return out

    def unpack_varint(self, max_bits=32):
        """
        Unpacks a varint.
        """

        number = 0
        for i in xrange(10):
            b = self.unpack("B")
            number |= (b & 0x7F) << 7*i
            if not b & 0x80:
                break

        if number & (1 << 31):
            number -= 1 << 32

        number_min = -1 << (max_bits - 1)
        number_max = +1 << (max_bits - 1)
        if not (number_min <= number < number_max):
            raise ValueError("varint does not fit in range: %d <= %d < %d"
                             % (number_min, number, number_max))

        return number

    # Packet ------------------------------------------------------------------

    @classmethod
    def pack_packet(cls, data, compression_threshold=-1):
        """
        Unpacks a packet frame. This method handles length-prefixing and
        compression.
        """

        if compression_threshold >= 0:
            # Compress data and prepend uncompressed data length
            if len(data) >= compression_threshold:
                data = cls.pack_varint(len(data)) + zlib.compress(data)
            else:
                data = cls.pack_varint(0) + data

        # Prepend packet length
        return cls.pack_varint(len(data), max_bits=32) + data

    def unpack_packet(self, cls, compression_threshold=-1):
        """
        Unpacks a packet frame. This method handles length-prefixing and
        compression.
        """
        body = self.read(self.unpack_varint(max_bits=32))
        buff = cls(body)
        if compression_threshold >= 0:
            uncompressed_length = buff.unpack_varint()
            if uncompressed_length > 0:
                body = zlib.decompress(buff.read())
                buff = cls(body)

        return buff

    # String ------------------------------------------------------------------

    @classmethod
    def pack_string(cls, text):
        """
        Pack a varint-prefixed utf8 string.
        """

        text = text.encode("utf-8")
        return cls.pack_varint(len(text), max_bits=16) + text

    def unpack_string(self):
        """
        Unpack a varint-prefixed utf8 string.
        """

        length = self.unpack_varint(max_bits=16)
        text = self.read(length).decode("utf-8")
        return text

    # JSON --------------------------------------------------------------------

    @classmethod
    def pack_json(cls, obj):
        """
        Serialize an object to JSON and pack it to a Minecraft string.
        """
        return cls.pack_string(json.dumps(obj))

    def unpack_json(self):
        """
        Unpack a Minecraft string and interpret it as JSON.
        """

        obj = json.loads(self.unpack_string())
        return obj

    # Chat --------------------------------------------------------------------

    @classmethod
    def pack_chat(cls, message):
        """
        Pack a Minecraft chat message.
        """
        from quarry.types import chat
        if not isinstance(message, chat.Message):
            message = chat.Message.from_string(message)
        return message.to_bytes()

    def unpack_chat(self):
        """
        Unpack a Minecraft chat message.
        """
        from quarry.types import chat
        return chat.Message.from_buff(self)

    # UUID --------------------------------------------------------------------

    @classmethod
    def pack_uuid(cls, uuid):
        """
        Packs a UUID.
        """

        return uuid.to_bytes()

    def unpack_uuid(self):
        """
        Unpacks a UUID.
        """

        return UUID.from_bytes(self.read(16))

    # Position ----------------------------------------------------------------

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

    # Block -------------------------------------------------------------------

    @classmethod
    def pack_block(cls, block, packer=None):
        """
        Packs a block.
        """
        if packer is None:
            packer = cls.pack_varint
        return packer(cls.block_map.encode_block(block))

    def unpack_block(self, unpacker=None):
        """
        Unpacks a block.
        """
        if unpacker is None:
            unpacker = self.unpack_varint
        return self.block_map.decode_block(unpacker())

    # Slot --------------------------------------------------------------------

    @classmethod
    def pack_slot(cls, item=None, count=1, damage=0, tag=None):
        """
        Packs a slot.
        """

        if item is None:
            return cls.pack('h', -1)

        item_id = cls.block_map.encode_item(item)
        return cls.pack('hbh', item_id, count, damage) + cls.pack_nbt(tag)

    def unpack_slot(self):
        """
        Unpacks a slot.
        """

        slot = {}
        item_id = self.unpack('h')
        if item_id == -1:
            slot['item'] = None
        else:
            slot['item'] = self.block_map.decode_item(item_id)
            slot['count'] = self.unpack('b')
            slot['damage'] = self.unpack('h')
            slot['tag'] = self.unpack_nbt()

        return slot

    # NBT ---------------------------------------------------------------------

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

    def unpack_nbt(self):
        """
        Unpacks NBT tag(s).
        """

        from quarry.types import nbt
        return nbt.TagRoot.from_buff(self)


    # Entity metadata ---------------------------------------------------------

    @classmethod
    def pack_entity_metadata(cls, metadata):
        """
        Packs entity metadata.
        """
        out = b""
        for ty_key, val in metadata.items():
            ty, key = ty_key
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

    def unpack_entity_metadata(self):
        """
        Unpacks entity metadata.
        """
        metadata = {}
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
            metadata[ty, key] = val
