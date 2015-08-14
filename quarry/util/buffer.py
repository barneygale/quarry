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
    def __init__(self):
        self.buff = b""
        self.pos = 0

    def length(self):
        return len(self.buff) - self.pos

    def add(self, d):
        self.buff += d

    def discard(self):
        self.buff = b""
        self.pos = 0

    def save(self):
        self.buff = self.buff[self.pos:]
        self.pos = 0

    def restore(self):
        self.pos = 0

    def read(self, l=None):
        if l is None:
            data = self.buff[self.pos:]
            self.pos = len(self.buff)
        else:
            if self.pos + l > len(self.buff):
                raise BufferUnderrun()

            data = self.buff[self.pos:self.pos+l]
            self.pos += l

        return data

    def unpack(self, ty):
        ty = ">"+ty
        s = struct.unpack(ty, self.read(struct.calcsize(ty)))
        return s[0] if len(s) == 1 else s

    def unpack_string(self):
        l = self.unpack_varint()
        return self.read(l).decode("utf-8")

    def unpack_json(self):
        return json.loads(self.unpack_string())

    def unpack_chat(self):
        def parse(obj):
            if isinstance(obj, basestring):
                return obj
            if isinstance(obj, list):
                return "".join((parse(e) for e in obj))
            if isinstance(obj, dict):
                out = ""
                if "translate" in obj:
                    if "with" in obj:
                        args = ", ".join((parse(e) for e in obj["with"]))
                    else:
                        args = ""
                    out += "%s{%s}" % (obj["translate"], args)
                if "text" in obj:
                    out += obj["text"]
                if "extra" in obj:
                    out += parse(obj["extra"])
                return out

        return parse(self.unpack_json())

    def unpack_varint(self):
        d = 0
        for i in range(5):
            b = self.unpack("B")
            d |= (b & 0x7F) << 7*i
            if not b & 0x80:
                break
        return d

    def unpack_uuid(self):
        return types.UUID.from_bytes(self.read(16))

    @classmethod
    def pack_raw(cls, data):
        return data

    @classmethod
    def pack(cls, ty, *data):
        return struct.pack(">"+ty, *data)

    @classmethod
    def pack_string(cls, data):
        data = data.encode("utf-8")
        return cls.pack_varint(len(data)) + data

    @classmethod
    def pack_json(cls, data):
        return cls.pack_string(json.dumps(data))

    @classmethod
    def pack_chat(cls, data):
        return cls.pack_json({"text": data})

    @classmethod
    def pack_varint(cls, d):
        o = b""
        while True:
            b = d & 0x7F
            d >>= 7
            o += cls.pack("B", b | (0x80 if d > 0 else 0))
            if d == 0:
                break
        return o

    @classmethod
    def pack_uuid(cls, d):
        return d.to_bytes()