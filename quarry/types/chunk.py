from collections import Sequence, MutableSequence
from bitstring import Bits, BitArray
import math


try:
    xrange
except NameError:
    xrange = range


class _NBTPaletteProxy(MutableSequence):
    def __init__(self, registry):
        self.registry = registry
        self.palette = []

    def insert(self, n, val):
        # FIXME: NBT chunk sections are *always* paletted, and so the format
        # diverges for palettes longer than 255 entries.
        if len(self.palette) >= 255:
            raise ValueError("Can't add more than 255 entries to NBT palette "
                             "proxy.")
        self.palette.insert(n, None)
        self[n] = val

    def __len__(self):
        return len(self.palette)

    def __delitem__(self, n):
        del self.palette[n]

    def __getitem__(self, n):
        from quarry.types import nbt

        block = self.registry.decode_block(self.palette[n])
        entry = nbt.TagCompound({'Name': nbt.TagString(block['name'])})
        if len(block) > 1:
            entry.value['Properties'] = nbt.TagCompound({
                key: nbt.TagString(value)
                for key, value in block.items()
                if key != "name"})

        return entry

    def __setitem__(self, n, tag):
        block = {'name': tag.value['Name'].value}
        properties = tag.value.get('Properties')
        if properties:
            block.update(properties.to_obj())

        self.palette[n] = self.registry.encode_block(block)


class LongArray(Sequence):

    # Constructors ------------------------------------------------------------
    def __init__(self, data, bits=None):
        self.data = data
        self.bits = bits or len(data) // (4096 if len(data) >= 16384 else 256)

    @classmethod
    def empty(cls, length, bits):
        return cls(BitArray(length=length*bits), bits)

    @classmethod
    def from_bytes(cls, data, bits=None):
        bs = BitArray(bytes=data)
        for idx in xrange(0, len(bs), 64):
            bs.reverse(idx, idx + 64)
        return cls(bs, bits)

    # Sequence methods --------------------------------------------------------

    def __len__(self):
        return len(self.data) // self.bits

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[o] for o in range(*n.indices(4096))]
        if not 0 <= n < len(self):
            raise IndexError(n)
        val = self.data[self.bits*n:self.bits*(n+1)]
        val._reverse()
        return val.uint

    def __setitem__(self, n, val):
        if isinstance(n, slice):
            for o in xrange(*n.indices(4096)):
                self[o] = val[o]
            return
        if not 0 <= n < len(self):
            raise IndexError(n)
        val = BitArray(uint=val, length=self.bits)
        val._reverse()
        self.data.overwrite(val, n * self.bits)

    # Other methods -----------------------------------------------------------

    def is_empty(self):
        return self.data.any()

    def resize(self, bits):
        # Danger!
        self.bits = bits
        self.data.clear()
        self.data.append(bits * 4096)

    def to_bytes(self):
        bs = self.data[:]
        for idx in xrange(0, len(bs), 64):
            bs.reverse(idx, idx + 64)
        return bs.bytes


class BlockArray(Sequence):

    # Constructors ------------------------------------------------------------

    def __init__(self, data, registry, palette, non_air=-1):
        self.data = data
        self.registry = registry
        self.palette = palette
        self.non_air = non_air
        if self.non_air == -1:
            self.non_air = [
                registry.is_air_block(obj) for obj in self].count(True)

    @classmethod
    def empty(cls, registry, count_non_air=True):
        """
        Creates an empty block array.
        """

        return cls(
            LongArray.empty(4096, 4),
            registry,
            [0],
            0 if count_non_air else None)

    @classmethod
    def from_nbt(cls, section, registry):
        """
        Creates a block array that uses the given NBT section tag as storage
        for block data and the palette. Minecraft 1.13+ only.
        """

        # Set up palette proxy
        nbt_palette = section.value['Palette']
        if isinstance(nbt_palette.value, _NBTPaletteProxy):
            proxy = nbt_palette.value
        else:
            proxy = _NBTPaletteProxy(registry)
            for entry in nbt_palette.value:
                proxy.append(entry)
            nbt_palette.value = proxy

        # Load block data
        return cls(
            section.value["BlockStates"].value,
            registry,
            proxy.palette)

    # Sequence methods --------------------------------------------------------

    def __len__(self):
        return 4096

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[o] for o in range(*n.indices(4096))]

        val = self.data[n]
        if self.palette:
            val = self.palette[val]
        val = self.registry.decode_block(val)
        return val

    def __setitem__(self, n, val):
        if isinstance(n, slice):
            for o in xrange(*n.indices(4096)):
                self[o] = val[o]
            return

        if self.non_air is not None:
            self.non_air += int(self.registry.is_air_block(self[n])) - \
                            int(self.registry.is_air_block(val))

        val = self.registry.encode_block(val)

        if self.palette:
            try:
                val = self.palette.index(val)
            except ValueError:
                self.repack(reserve=1)

                if self.palette:
                    self.palette.append(val)
                    val = len(self.palette) - 1

        self.data[n] = val

    # Other methods -----------------------------------------------------------

    def is_empty(self):
        """
        Checks if this block array is entirely air. You may wish to call
        ``repack()`` before this method to avoid false negatives.
        """
        if self.palette:
            return self.palette == [0]
        else:
            return not self.data.any()

    def repack(self, reserve=None):
        """
        Re-packs internal data to use the smallest possible bits-per-block by
        eliminating unused palette entries. This operation is slow as it walks
        all blocks to determine the new palette.
        """
        if reserve is None:
            # Recompute the palette by walking all blocks
            palette = []
            for block in self:
                if block not in palette:
                    palette.append(block)
            palette = [self.registry.encode_block(block) for block in palette]
            palette_len = len(palette)
        else:
            if not self.palette:
                # Reserving space in an unpaletted array is a no-op.
                return

            palette = self.palette[:]
            palette_len = len(palette) + reserve

        # Compute new bits
        bits = self.calc_bits(palette_len)
        if bits > 8:
            palette = []

        if self.data.bits == bits:
            # Nothing to do.
            return

        # Save contents
        values = self[:]

        # Update internals
        self.data.resize(bits)
        self.palette.clear()
        self.palette.extend(palette)

        # Load contents
        self[:] = values

    def calc_bits(self, length):
        bits = int(math.ceil(math.log(length, 2)))
        if bits < 4:
            return 4
        elif bits > 8:
            return self.registry.max_bits
        else:
            return bits


class LightArray(Sequence):

    # Constructors ------------------------------------------------------------

    def __init__(self, data):
        self.data = data

    @classmethod
    def empty(cls):
        """
        Creates an empty light array.
        """
        return cls([0] * 2048)

    @classmethod
    def from_nbt(cls, section, sky=True):
        """
        Creates a light array that uses the given NBT section tag as storage
        for light data. Minecraft 1.13+ only.
        """
        return cls(section.value['SkyLight' if sky else 'BlockLight'].value)

    # Sequence methods --------------------------------------------------------

    def __len__(self):
        return 4096

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[o] for o in xrange(*n.indices(4096))]
        assert isinstance(n, int)
        idx, off = divmod(n, 2)
        val = self.data[idx]
        if off == 0:
            return val & 0x0F
        else:
            return val >> 4

    def __setitem__(self, n, val):
        assert isinstance(n, int)
        idx, off = divmod(n, 2)
        if off == 0:
            self.data[idx] = (self.data[idx] & 0xF0) | val
        else:
            self.data[idx] = (self.data[idx] & 0x0F) | (val << 4)
