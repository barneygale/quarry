import struct
import json

from quarry.util import types

# Python 3 compat
try:
  basestring
except NameError:
  basestring = str

class BufferUnderrun(Exception):
    pass


class Buffer(object):
    buff = b""
    pos = 0

    def __len__(self):
        return len(self.buff) - self.pos

    def add(self, data):
        self.buff += data

    def save(self):
        self.buff = self.buff[self.pos:]
        self.pos = 0

    def restore(self):
        self.pos = 0

    def discard(self):
        self.pos = len(self.buff)

    def read(self, length=None):
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
        fmt = ">"+fmt
        length = struct.calcsize(fmt)
        fields = struct.unpack(fmt, self.read(length))
        if len(fields) == 1:
            fields = fields[0]
        return fields

    def unpack_string(self):
        length = self.unpack_varint()
        text = self.read(length).decode("utf-8")
        return text

    def unpack_json(self):
        obj = json.loads(self.unpack_string())
        return obj

    def unpack_chat(self):
        def parse(obj):
            if isinstance(obj, basestring):
                return obj
            if isinstance(obj, list):
                return "".join((parse(e) for e in obj))
            if isinstance(obj, dict):
                text = ""
                if "translate" in obj:
                    if "with" in obj:
                        args = ", ".join((parse(e) for e in obj["with"]))
                    else:
                        args = ""
                    text += "%s{%s}" % (obj["translate"], args)
                if "text" in obj:
                    text += obj["text"]
                if "extra" in obj:
                    text += parse(obj["extra"])
                return text

        text = parse(self.unpack_json())
        return text

    def unpack_varint(self):
        number = 0
        for i in range(5):
            b = self.unpack("B")
            number |= (b & 0x7F) << 7*i
            if not b & 0x80:
                break
        return number

    def unpack_uuid(self):
        return types.UUID.from_bytes(self.read(16))

    @classmethod
    def pack(cls, fmt, *fields):
        return struct.pack(">"+fmt, *fields)

    @classmethod
    def pack_string(cls, text):
        text = text.encode("utf-8")
        return cls.pack_varint(len(text)) + text

    @classmethod
    def pack_json(cls, obj):
        return cls.pack_string(json.dumps(obj))

    @classmethod
    def pack_chat(cls, text):
        return cls.pack_json({"text": text})

    @classmethod
    def pack_varint(cls, number):
        out = b""
        while True:
            b = number & 0x7F
            number >>= 7
            out += cls.pack("B", b | (0x80 if number > 0 else 0))
            if number == 0:
                break
        return out

    @classmethod
    def pack_uuid(cls, uuid):
        return uuid.to_bytes()