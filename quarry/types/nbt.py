import collections
import functools
import gzip
import time
import zlib

from quarry.types.buffer import Buffer

_kinds = {}
_ids = {}


# Base types ------------------------------------------------------------------

@functools.total_ordering
class _Tag(object):
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_bytes(cls, bytes):
        return cls.from_buff(Buffer(bytes))

    @classmethod
    def from_buff(cls, buff):
        raise NotImplementedError

    def to_bytes(self):
        raise NotImplementedError

    def to_obj(self):
        return self.value

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.value)

    def __eq__(self, other):
        return self.to_obj() == other.to_obj()

    def __lt__(self, other):
        return self.to_obj() < other.to_obj()


class _DataTag(_Tag):
    fmt = None

    @classmethod
    def from_buff(cls, buff):
        return cls(buff.unpack(cls.fmt))

    def to_bytes(self):
        return Buffer.pack(self.fmt, self.value)


class _ArrayTag(_Tag):
    fmt = None

    @classmethod
    def from_buff(cls, buff):
        array_length = buff.unpack('i')
        return cls(list(buff.unpack_array(cls.fmt, array_length)))

    def to_bytes(self):
        return (
            Buffer.pack('i', len(self.value)) +
            Buffer.pack_array(self.fmt, self.value))


# NBT tags --------------------------------------------------------------------

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
    fmt = 'b'


class TagIntArray(_ArrayTag):
    fmt = 'i'


class TagLongArray(_ArrayTag):
    fmt = 'q'


class TagUnsignedLongArray(_ArrayTag):
    fmt = 'Q'


class TagList(_Tag):
    @classmethod
    def from_buff(cls, buff):
        inner_kind_id, array_length = buff.unpack('bi')
        inner_kind = _kinds[inner_kind_id]
        return cls([inner_kind.from_buff(buff) for _ in range(array_length)])

    def to_bytes(self):
        if len(self.value) > 0:
            head = self.value[0]
        else:
            head = TagByte(0)

        return Buffer.pack('bi', _ids[type(head)], len(self.value)) + \
               b"".join(tag.to_bytes() for tag in self.value)

    def to_obj(self):
        return [tag.to_obj() for tag in self.value]


class TagCompound(_Tag):
    root = False
    preserve_order = False

    @classmethod
    def from_buff(cls, buff):
        if cls.preserve_order:
            value = collections.OrderedDict()
        else:
            value = {}

        while True:
            kind_id = buff.unpack('b')
            if kind_id == 0:
                return cls(value)
            kind = _kinds[kind_id]
            name = TagString.from_buff(buff).value

            # ~~ Evil Hack Alert ~~
            # Signed bitwise arithmetic in Python is simultaneously elegant and
            # baffling. Special-case the BlockStates array to use /unsigned/
            # integers, in contravention of spec, but to the great relief of
            # this programmer.
            if kind is TagLongArray and name == "BlockStates":
                kind = TagUnsignedLongArray

            tag = kind.from_buff(buff)
            value[name] = tag
            if cls.root:
                return cls(value)

    def to_bytes(self):
        string = b""
        for name, tag in self.value.items():
            string += Buffer.pack('b', _ids[type(tag)])
            string += TagString(name).to_bytes()
            string += tag.to_bytes()

        if len(self.value) == 0 or not self.root:
            string += Buffer.pack('b', 0)

        return string

    def to_obj(self):
        return dict((name, tag.to_obj()) for name, tag in self.value.items())

    def update(self, other_tag):
        for name, new_tag in other_tag.value.items():
            old_tag = self.value.get(name)

            if old_tag and not new_tag:
                del self.value[name]
            elif isinstance(old_tag, TagCompound) \
                    and isinstance(new_tag, TagCompound):
                self.value[name].update(new_tag)
            else:
                self.value[name] = new_tag


class TagRoot(TagCompound):
    root = True

    @property
    def body(self):
        return self.value[u""]


# Register tags ---------------------------------------------------------------

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
_kinds[12] = TagLongArray
_ids.update({v: k for k, v in _kinds.items()})
_ids[TagUnsignedLongArray] = 12


# Files -----------------------------------------------------------------------

class NBTFile(object):
    root_tag = None

    def __init__(self, root_tag):
        self.root_tag = root_tag

    @classmethod
    def load(cls, path):
        with gzip.open(path, 'rb') as fd:
            return cls(TagRoot.from_bytes(fd.read()))

    def save(self, path):
        with gzip.open(path, 'wb') as fd:
            fd.write(self.root_tag.to_bytes())


class RegionFile(object):
    """
    Experimental support for the Minecraft world storage format (``.mca``).
    """
    def __init__(self, path):
        self.fd = open(path, "r+b")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fd.close()

    def close(self):
        """
        Closes the region file.
        """
        self.fd.close()

    def save_chunk(self, chunk):
        """
        Saves the given chunk, which should be a ``TagRoot``, to the region
        file.
        """

        # Compress chunk
        chunk_x = chunk.body.value["Level"].value["xPos"].value
        chunk_z = chunk.body.value["Level"].value["zPos"].value
        chunk = zlib.compress(chunk.to_bytes())
        chunk = Buffer.pack('IB', len(chunk), 2) + chunk
        chunk_length = 1 + (len(chunk) - 1) // 4096

        # Load extents
        extents = [(0, 2)]
        self.fd.seek(0)
        buff = Buffer(self.fd.read(4096))
        for idx in range(1024):
            z, x = divmod(idx, 32)
            entry = buff.unpack('I')
            offset, length = entry >> 8, entry & 0xFF
            if offset > 0 and not (x == chunk_x and z == chunk_z):
                extents.append((offset, length))
        extents.sort()
        extents.append((extents[-1][0] + extents[-1][1] + chunk_length, 0))

        # Compute new extent
        for idx in range(len(extents) - 1):
            start = extents[idx][0] + extents[idx][1]
            end = extents[idx+1][0]
            if (end - start) >= chunk_length:
                chunk_offset = start
                extents.insert(idx+1, (chunk_offset, chunk_length))
                break

        # Write extent header
        self.fd.seek(4 * (32 * chunk_z + chunk_x))
        self.fd.write(Buffer.pack(
            'I', (chunk_offset << 8) | (chunk_length & 0xFF)))

        # Write timestamp header
        self.fd.seek(4096 + 4 * (32 * chunk_z + chunk_x))
        self.fd.write(Buffer.pack('I', int(time.time())))

        # Write chunk
        self.fd.seek(4096 * chunk_offset)
        self.fd.write(chunk)

        # Truncate file
        self.fd.seek(4096 * extents[-1][0])
        self.fd.truncate()

    def load_chunk(self, chunk_x, chunk_z):
        """
        Loads the chunk at the given co-ordinates from the region file.
        The co-ordinates should range from 0 to 31. Returns a ``TagRoot``.
        """

        buff = Buffer()

        # Read extent header
        self.fd.seek(4 * (32 * chunk_z + chunk_x))
        buff.add(self.fd.read(4))
        entry = buff.unpack('I')
        chunk_offset, chunk_length = entry >> 8, entry & 0xFF
        if chunk_offset == 0:
            raise ValueError((chunk_x, chunk_z))

        # Read chunk
        self.fd.seek(4096 * chunk_offset)
        buff.add(self.fd.read(4096 * chunk_length))
        chunk = buff.read(buff.unpack('IB')[0])
        chunk = zlib.decompress(chunk)
        chunk = TagRoot.from_bytes(chunk)
        return chunk

    def load_chunk_section(self, chunk_x, chunk_y, chunk_z):
        """
        Loads the chunk section at the given co-ordinates from the region file.
        The co-ordinates should range from 0 to 31. Returns a ``TagRoot``.
        """

        chunk = self.load_chunk(chunk_x, chunk_z)
        sections = chunk.body.value["Level"].value["Sections"].value
        for section in sections:
            if section.value["Y"].value == chunk_y:
                return chunk, section

        raise ValueError((chunk_x, chunk_y, chunk_z))


# Debug -----------------------------------------------------------------------

def alt_repr(tag, level=0):
    """
    Returns a human-readable representation of a tag using the same format as
    used the NBT specification.
    """
    name = lambda kind: type(kind).__name__.replace("Tag", "TAG_")

    if isinstance(tag, _ArrayTag):
        return "%s%s: %d entries" % (
            "  " * level,
            name(tag),
            len(tag.value))

    elif isinstance(tag, TagList):
        return "%s%s: %d entries\n%s{\n%s\n%s}" % (
            "  " * level,
            name(tag),
            len(tag.value),
            "  " * level,
            u"\n".join(alt_repr(tag, level+1) for tag in tag.value),
            "  " * level)

    elif isinstance(tag, TagRoot):
        return u"\n".join(
                alt_repr(tag, level).replace(': ', '("%s"): ' % name, 1)
                for name, tag in tag.value.items())

    elif isinstance(tag, TagCompound):
        return "%s%s: %d entries\n%s{\n%s\n%s}" % (
            "  " * level,
            name(tag),
            len(tag.value),
            "  " * level,
            u"\n".join(
                alt_repr(tag, level+1).replace(': ', '("%s"): ' % name, 1)
                for name, tag in tag.value.items()),
            "  " * level)

    elif isinstance(tag, TagString):
        return '%s%s: "%s"' % (
            "  " * level,
            name(tag),
            tag.value)

    else:
        return "%s%s: %r" % (
            "  " * level,
            name(tag),
            tag.value)
