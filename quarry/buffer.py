import struct
import json


class BufferUnderrun(Exception):
    pass


class Buffer(object):
    def __init__(self):
        self.buff1 = ""
        self.buff2 = ""

    def length(self):
        return len(self.buff1)

    def add(self, d):
        self.buff1 += d

    def discard(self):
        self.buff1 = ""

    def save(self):
        self.buff2 = self.buff1

    def restore(self):
        self.buff1 = self.buff2

    def unpack_all(self):
        d = self.buff1
        self.discard()
        return d

    def unpack_raw(self, l):
        if len(self.buff1) < l:
            raise BufferUnderrun()
        d, self.buff1 = self.buff1[:l], self.buff1[l:]
        return d

    def unpack(self, ty):
        s = struct.unpack(">"+ty, self.unpack_raw(struct.calcsize(ty)))
        return s[0] if len(ty) == 1 else s

    def unpack_string(self):
        l = self.unpack_varint()
        return self.unpack_raw(l).decode("utf-8")

    def unpack_json(self):
        return json.loads(self.unpack_string())

    def unpack_array(self):
        l = self.unpack("h")
        return self.unpack_raw(l)

    def unpack_varint(self):
        d = 0
        for i in range(5):
            b = self.unpack("B")
            d |= (b & 0x7F) << 7*i
            if not b & 0x80:
                break
        return d

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
    def pack_array(cls, data):
        return cls.pack("h", len(data)) + data

    @classmethod
    def pack_varint(cls, d):
        o = ""
        while True:
            b = d & 0x7F
            d >>= 7
            o += cls.pack("B", b | (0x80 if d > 0 else 0))
            if d == 0:
                break
        return o