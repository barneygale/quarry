from collections import Sequence, MutableSequence
from bitstring import BitArray, Bits
import math


try:
    xrange
except NameError:
    xrange = range


def twiddle(bitstring, width):
    """
    Performs an in-place reversal of chunks in the given bitstring.
    """

    for idx in xrange(0, len(bitstring), width):
        bitstring.reverse(idx, idx + width)
    return bitstring


def get_width(length, full_width):
    """
    Returns the number of bits used by Minecraft to represent indices into a
    list of the given length.
    """

    width = int(math.ceil(math.log(length, 2)))
    if width < 4:
        return 4
    elif width > 8:
        return full_width
    else:
        return width


class PackedArray(Sequence):
    """
    An array where entries are packed into an arbitrary number of bits.
    """

    #: The `bitstring.BitArray()` object used for storage.
    storage = None

    #: The width in bits of chunks. Used in (de)serialization.
    chunk_width = None

    #: The width in bits of values.
    value_width = None

    #: The most recent result of `to_bytes`
    cache_bytes = None

    #: True when `to_bytes` will perform a fresh serialization
    cache_dirty = None

    def __repr__(self):
        return "<PackedArray length=%d chunk=%d value=%d %s>" % (
            len(self),
            self.chunk_width,
            self.value_width,
            "dirty" if self.cache_dirty else "clean")

    # Constructors ------------------------------------------------------------

    def __init__(self, storage, chunk_width, value_width, bytes=None):
        self.storage = storage
        self.chunk_width = chunk_width
        self.value_width = value_width
        self.cache_bytes = bytes
        self.cache_dirty = bytes is None

    @classmethod
    def empty(cls, length, chunk_width, value_width):
        """
        Creates an empty array.
        """

        storage = BitArray(length=length*value_width)
        return cls(storage, chunk_width, value_width)

    @classmethod
    def empty_light(cls):
        """
        Creates an empty array suitable for storing light data.
        """

        return cls.empty(4096, 8, 4)

    @classmethod
    def empty_block(cls):
        """
        Creates an empty array suitable for storing block data.
        """

        return cls.empty(4096, 64, 4)

    @classmethod
    def empty_height(cls):
        """
        Creates an empty array suitable for storing height data.
        """

        return cls.empty(256, 64, 9)

    @classmethod
    def from_bytes(cls, bytes, chunk_width, value_width=None):
        """
        Deserialize a packed array from the given bytes.
        """

        storage = BitArray(bytes=bytes)

        if value_width is None:
            length = len(storage)
            if length < 2048:
                value_width = chunk_width
            elif length < 16384 and length % 256 == 0:
                value_width = length // 256
            elif length < 65536 and length % 4096 == 0:
                value_width = length // 4096
            else:
                value_width = chunk_width

        if chunk_width != value_width:
            twiddle(storage, chunk_width)
            twiddle(storage, value_width)

        return cls(storage, chunk_width, value_width, bytes)

    @classmethod
    def from_light_bytes(cls, bytes):
        """
        Deserialize a packed array from the given light data bytes.
        """

        return cls.from_bytes(bytes, 8, 4)

    @classmethod
    def from_block_bytes(cls, bytes):
        """
        Deserialize a packed array from the given block data bytes.
        """

        return cls.from_bytes(bytes, 64)

    @classmethod
    def from_height_bytes(cls, bytes):
        """
        Deserialize a packed array from the given height data bytes.
        """

        return cls.from_bytes(bytes, 64, 9)

    # Instance methods --------------------------------------------------------

    def to_bytes(self):
        """
        Serialize this packed array to bytes.
        """

        if self.cache_dirty:
            storage = self.storage[:]
            if self.chunk_width != self.value_width:
                twiddle(storage, self.value_width)
                twiddle(storage, self.chunk_width)
            self.cache_bytes = storage.bytes
            self.cache_dirty = False
        return self.cache_bytes

    def is_empty(self):
        """
        Returns true if this packed array is entirely zeros.
        """

        return not self.storage.any(True)

    def purge(self, value_width):
        """
        Re-initialize the packed array to use a different value width,
        **destroying stored data in the process**.
        """

        length = len(self)
        self.storage.clear()
        self.storage.append(value_width * length)
        self.value_width = value_width
        self.cache_dirty = True

    # Sequence methods --------------------------------------------------------

    def __len__(self):
        return len(self.storage) // self.value_width

    def __iter__(self):
        w = self.value_width
        for idx in xrange(len(self)):
            yield self.storage._slice(w*idx, w*(idx+1)).uint

    def __getitem__(self, item):
        w = self.value_width
        if isinstance(item, slice):
            return [self.storage._slice(w*idx, w*(idx+1)).uint
                    for idx in xrange(*item.indices(len(self)))]
        else:
            if not 0 <= item < len(self):
                raise IndexError(item)
            return self.storage._slice(w*item, w*(item+1)).uint

    def __setitem__(self, item, value):
        w = self.value_width
        if isinstance(item, slice):
            for idx, value in zip(xrange(*item.indices(len(self))), value):
                self.storage._overwrite(
                    bs=Bits(uint=value, length=w),
                    pos=idx*w)
        else:
            self.storage._overwrite(
                bs=Bits(uint=value, length=w),
                pos=item*w)
        self.cache_dirty = True


class BlockArray(Sequence):
    """
    An array where entries are packed into an arbitrary number of bits.

    A palette is used when there are fewer than 256 unique values; the value
    width varies from 4 to 8 bits depending on the sice of the palette. When
    more than 256 unique values are present, the palette is unused and values
    are stored directly.

    The number of non-air blocks is recorded for lighting purposes.
    """

    #: The `PackedArray` object used for storage.
    storage = None

    #: List of encoded block values. Empty when palette is not used.
    palette = None

    #: The `Registry` object used to encode/decode blocks
    registry = None

    #: The number of non-air blocks
    non_air = None

    def __repr__(self):
        return "<BlockArray palette=%d storage=%r>" \
               % (len(self.palette), self.storage)

    # Constructors ------------------------------------------------------------

    def __init__(self, storage, palette, registry, non_air=-1):
        self.storage = storage
        self.palette = palette
        self.registry = registry
        self.non_air = non_air
        if non_air == -1:
            self.non_air = [
                registry.is_air_block(obj) for obj in self].count(False)

    @classmethod
    def empty(cls, registry, non_air=-1):
        """
        Creates an empty block array.
        """

        storage = PackedArray.empty(4096, 64, 4)
        palette = [0]
        return cls(storage, palette, registry, non_air)

    @classmethod
    def from_bytes(cls, bytes, palette, registry, non_air=-1):
        """
        Deserialize a block array from the given bytes.
        """

        storage = PackedArray.from_block_bytes(bytes)
        return cls(storage, palette, registry, non_air)

    @classmethod
    def from_nbt(cls, section, registry, non_air=-1):
        """
        Creates a block array that uses the given NBT section tag as storage
        for block data and the palette. Minecraft 1.13+ only.
        """

        nbt_palette = section.value['Palette']
        if isinstance(nbt_palette.value, _NBTPaletteProxy):
            proxy = nbt_palette.value
        else:
            proxy = _NBTPaletteProxy(registry)
            for entry in nbt_palette.value:
                proxy.append(entry)
            nbt_palette.value = proxy

        storage = section.value["BlockStates"].value
        palette = proxy.palette
        return cls(storage, palette, registry, non_air)

    # Instance methods --------------------------------------------------------

    def to_bytes(self):
        """
        Serialize this block array to bytes.
        """

        return self.storage.to_bytes()

    def is_empty(self):
        """
        Returns true if this block array is entirely air.
        """

        if self.palette == [0]:
            return True
        else:
            return self.storage.is_empty()

    def repack(self, reserve=None):
        """
        Re-packs internal data to use the smallest possible bits-per-block by
        eliminating unused palette entries. This operation is slow as it walks
        all blocks to determine the new palette.
        """

        # If no reserve is given, we re-compute the palette by walking blocks
        if reserve is None:
            palette = sorted(set(self))
            palette_len = len(palette)

        # Otherwise we just ensure we have enough space to store new entries.
        elif self.palette:
            palette = self.palette[:]
            palette_len = len(palette) + reserve

        # Reserving space in an unpaletted array is a no-op.
        else:
            return

        # Compute new value width
        value_width = get_width(palette_len, self.registry.max_bits)

        # Exit if there's no change in value width needed
        if value_width == self.storage.value_width:
            return

        # Switch to unpaletted operation if necessary
        if value_width > 8:
            palette = []

        # Save contents
        values = self[:]

        # Update internals
        self.storage.purge(value_width)
        self.palette[:] = palette

        # Load contents
        self[:] = values

    # Sequence methods --------------------------------------------------------

    def __len__(self):
        return 4096

    def __getitem__(self, item):
        if isinstance(item, slice):
            values = []
            for value in self.storage[item.start:item.stop:item.step]:
                if self.palette:
                    value = self.palette[value]
                value = self.registry.decode_block(value)
                values.append(value)
            return values
        else:
            value = self.storage[item]
            if self.palette:
                value = self.palette[value]
            value = self.registry.decode_block(value)
            return value

    def __setitem__(self, item, value):
        if isinstance(item, slice):
            for idx in xrange(*item.indices(4096)):
                self[idx] = value[idx]
            return

        if self.non_air is not None:
            self.non_air += int(self.registry.is_air_block(self[item])) - \
                            int(self.registry.is_air_block(value))

        value = self.registry.encode_block(value)

        if self.palette:
            try:
                value = self.palette.index(value)
            except ValueError:
                self.repack(reserve=1)

                if self.palette:
                    self.palette.append(value)
                    value = len(self.palette) - 1

        self.storage[item] = value

    def __iter__(self):
        for value in self.storage:
            if self.palette:
                value = self.palette[value]
            value = self.registry.decode_block(value)
            yield value

    def __contains__(self, value):
        if self.palette:
            if self.registry.encode_block(value) not in self.palette:
                return False
        return super(BlockArray, self).__contains__(value)

    def index(self, value, start=0, stop=None):
        if self.palette:
            if self.registry.encode_block(value) not in self.palette:
                raise ValueError
        return super(BlockArray, self).index(value, start, stop)

    def count(self, value):
        if self.palette:
            if self.registry.encode_block(value) not in self.palette:
                return 0
        return super(BlockArray, self).count(value)


class _NBTPaletteProxy(MutableSequence):
    def __init__(self, registry):
        self.registry = registry
        self.palette = []

    def insert(self, idx, value):
        # FIXME: NBT chunk sections are *always* paletted, and so the format
        # diverges for palettes longer than 255 entries.
        if len(self.palette) >= 255:
            raise ValueError("Can't add more than 255 entries to NBT palette "
                             "proxy.")
        self.palette.insert(idx, None)
        self[idx] = value

    def __len__(self):
        return len(self.palette)

    def __delitem__(self, idx):
        del self.palette[idx]

    def __getitem__(self, idx):
        from quarry.types import nbt

        block = self.registry.decode_block(self.palette[idx])
        entry = nbt.TagCompound({'Name': nbt.TagString(block['name'])})
        if len(block) > 1:
            entry.value['Properties'] = nbt.TagCompound({
                key: nbt.TagString(value)
                for key, value in block.items()
                if key != "name"})

        return entry

    def __setitem__(self, idx, tag):
        block = {'name': tag.value['Name'].value}
        properties = tag.value.get('Properties')
        if properties:
            block.update(properties.to_obj())

        self.palette[idx] = self.registry.encode_block(block)
