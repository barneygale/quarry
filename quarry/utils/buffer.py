import struct
import json
import re

from quarry.data.chat_styles import code_by_name, code_by_prop
from quarry.utils import types
from quarry.utils.errors import ProtocolError

# Python 3 compat
try:
    basestring
except NameError:  # pragma: no cover
    basestring = str


class BufferUnderrun(Exception):
    pass


class Buffer(object):
    buff = b""
    pos = 0

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
        Read *length* bytes from the beginning of the buffer buffer, or all
        bytes if *length* is ``None``
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
        Unpack a struct from the buffer. The format accepted is the same as
        for ``struct.unpack()``.
        """

        fmt = ">"+fmt
        length = struct.calcsize(fmt)
        fields = struct.unpack(fmt, self.read(length))
        if len(fields) == 1:
            fields = fields[0]
        return fields

    def unpack_string(self):
        """
        Unpack a Minecraft string (varint-prefixed utf8) from the buffer.
        """

        length = self.unpack_varint(max_bits=16)
        text = self.read(length).decode("utf-8")
        return text

    def unpack_json(self):
        """
        Unpack a Minecraft string from the buffer and interpret it as JSON.
        """

        obj = json.loads(self.unpack_string())
        return obj

    def unpack_chat(self, strip_styles=True):
        """
        Unpack a Minecraft chat message from the buffer. Minecraft uses a
        JSON format to send chat messages; this method retrieves a plaintext
        representation, optionally including styles encoded using oldschool
        chat codes (U+00A7 plus one character). For more control, use
        :meth:`unpack_json`.
        """

        def parse(obj):
            if isinstance(obj, basestring):
                return obj
            if isinstance(obj, list):
                return "".join((parse(e) for e in obj))
            if isinstance(obj, dict):
                text = ""
                for prop, code in code_by_prop.items():
                    if obj.get(prop):
                        text += u"\u00a7" + code
                if "color" in obj:
                    text += u"\u00a7" + code_by_name[obj["color"]]
                if "translate" in obj:
                    text += obj["translate"]
                    if "with" in obj:
                        args = ", ".join((parse(e) for e in obj["with"]))
                        text += "{%s}" % args
                if "text" in obj:
                    text += obj["text"]
                if "extra" in obj:
                    text += parse(obj["extra"])
                return text

        text = parse(self.unpack_json())
        if strip_styles:
            text = self.strip_chat_styles(text)
        return text

    def unpack_varint(self, max_bits=32, signed=False):
        """
        Unpacks a varint from the buffer.
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
                raise ProtocolError("varint cannot be negative: %d" % number)

        number_min = -1 << (max_bits - 1)
        number_max = +1 << (max_bits - 1)
        if not (number_min <= number < number_max):
            raise ProtocolError("varint does not fit in range: %d <= %d < %d"
                                % (number_min, number, number_max))

        return number

    def unpack_uuid(self):
        """
        Unpacks a UUID from the buffer.
        """

        return types.UUID.from_bytes(self.read(16))

    def unpack_position(self):
        """
        Unpacks a Position from the buffer.
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
        Unpacks a Slot from the buffer.
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
        Unpacks NBT tag(s) from the buffer.
        """

        from quarry.utils import nbt
        return nbt.NamedTag.from_buff(self)

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
    def pack_chat(cls, text):
        """
        Pack a Minecraft chat message. This method accepts plaintext; to send
        colours and other formatting use :meth:`pack_json`.
        """

        return cls.pack_json({"text": text})

    @classmethod
    def pack_varint(cls, number, max_bits=32, signed=False):
        """
        Packs a varint.
        """

        number_min = -1 << (max_bits - 1)
        number_max = +1 << (max_bits - 1)
        if not (number_min <= number < number_max):
            raise ProtocolError("varint does not fit in range: %d <= %d < %d"
                                % (number_min, number, number_max))

        if number < 0:
            if signed:
                number += 1<<32
            else:
                raise ProtocolError("varint cannot be negative: %d" % number)

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
    def pack_nbt(cls, tag):
        return tag.to_bytes()

    @classmethod
    def strip_chat_styles(cls, text):
        """
        Strips chat styles from text.
        """
        return re.sub(u"\u00A7.", "", text)