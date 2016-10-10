import gzip

from .buffer import Buffer

_kinds = {}
_ids = {}


# Base types --------------------------------------------------------------------------------------

class _Tag(object):
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_buff(cls, buff):
        raise NotImplementedError

    def to_bytes(self):
        raise NotImplementedError

    def to_obj(self):
        return self.value

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.value)


class _DataTag(_Tag):
    fmt = None

    @classmethod
    def from_buff(cls, buff):
        return cls(buff.unpack(cls.fmt))

    def to_bytes(self):
        return Buffer.pack(self.fmt, self.value)


class _ArrayTag(_Tag):
    inner_kind = None

    def __init__(self, value, inner_kind):
        super(_ArrayTag, self).__init__(value)
        self.inner_kind = inner_kind

    @classmethod
    def from_buff(cls, buff, inner_kind=None):
        if inner_kind is None:
            inner_kind = cls.inner_kind
        array_length = buff.unpack('i')
        return cls([inner_kind.from_buff(buff).value for _ in range(array_length)], inner_kind)

    def to_bytes(self):
        return (
            Buffer.pack('i', len(self.value)) +
            b"".join(
                self.inner_kind(elem).to_bytes() for elem in self.value))

    def to_obj(self):
        return [self.inner_kind(elem).to_obj() for elem in self.value]

    def __repr__(self):
        return "%s<%s>(%s)" % (type(self).__name__, self.inner_kind.__name__, self.value)


# Special types -----------------------------------------------------------------------------------

class NamedTag(_Tag):
    def __init__(self, value, name):
        super(NamedTag, self).__init__(value)
        self.name = name

    @classmethod
    def from_buff(cls, buff):
        kind_id = buff.unpack('b')
        if kind_id == 0:
            return None
        kind = _kinds[kind_id]
        name = TagString.from_buff(buff).value
        value = kind.from_buff(buff)
        return cls(value, name)

    def to_bytes(self):
        return (
            Buffer.pack('b', _ids[type(self.value)]) +
            TagString(self.name).to_bytes() +
            self.value.to_bytes())

    def to_obj(self):
        return self.name, self.value.to_obj()

    def __repr__(self):
        return "%s(%r, %r)" % (type(self).__name__, self.name, self.value)


# NBT tags ----------------------------------------------------------------------------------------

class TagByte(_DataTag):
    fmt = 'b'


class TagShort(_DataTag):
    fmt = 'h'


class TagInt(_DataTag):
    fmt = 'i'


class TagLong(_DataTag):
    fmt = 'q'


class TagFloat(_DataTag):
    fmt = 'f'


class TagDouble(_DataTag):
    fmt = 'd'


class TagString(_Tag):

    @classmethod
    def from_buff(cls, buff):
        string_length = buff.unpack('H')
        return cls(buff.read(string_length).decode('utf8'))

    def to_bytes(self):
        data = self.value.encode('utf8')
        return Buffer.pack('H', len(data)) + data


class TagByteArray(_ArrayTag):
    inner_kind = TagByte


class TagIntArray(_ArrayTag):
    inner_kind = TagInt


class TagList(_ArrayTag):

    @classmethod
    def from_buff(cls, buff):
        inner_kind_id = buff.unpack('b')
        inner_kind = _kinds[inner_kind_id]
        return super(TagList, cls).from_buff(buff, inner_kind)

    def to_bytes(self):
        return Buffer.pack('b', _ids[self.inner_kind]) + super(TagList, self).to_bytes()


class TagCompound(_Tag):

    @classmethod
    def from_buff(cls, buff):
        value = []
        while True:
            tag = NamedTag.from_buff(buff)
            if tag is None:
                return cls(value)
            value.append(tag)

    def to_bytes(self):
        return b"".join(tag.to_bytes() for tag in self.value) + Buffer.pack('b', 0)

    def to_obj(self):
        return dict(tag.to_obj() for tag in self.value)


# Register tags -----------------------------------------------------------------------------------

_kinds[0] = type(None)
_kinds[1] = TagByte
_kinds[2] = TagShort
_kinds[3] = TagInt
_kinds[4] = TagLong
_kinds[5] = TagFloat
_kinds[6] = TagDouble
_kinds[7] = TagByteArray
_kinds[8] = TagString
_kinds[9] = TagList
_kinds[10] = TagCompound
_kinds[11] = TagIntArray
_ids.update({v: k for k, v in _kinds.items()})

# Files -------------------------------------------------------------------------------------------

class NBTFile(object):
    def __init__(self, root_tag):
        self.root_tag = root_tag

    @classmethod
    def load(cls, path):
        with gzip.open(path, 'rb') as fd:
            buff = Buffer()
            buff.add(fd.read())
            return cls(NamedTag.from_buff(buff))

    def save(self, path):
        with gzip.open(path, 'wb') as fd:
            fd.write(self.root_tag.to_bytes())
