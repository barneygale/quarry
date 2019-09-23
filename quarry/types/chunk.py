from collections import Sequence, MutableSequence
from bitstring import BitArray
import math


try:
    xrange
except NameError:
    xrange = range


def length_to_bits(max_bits, length):
    bits = int(math.ceil(math.log(length, 2)))
    if bits < 4:
        return 4
    elif bits > 8:
        return max_bits
    else:
        return bits


def index_to_addresses(index, bits):
    idx0 = (index * bits) // 64
    idx1 = ((index + 1) * bits - 1) // 64
    len0 = 64 - (index * bits) % 64
    len1 = bits - len0

    if idx0 == idx1:
        yield 0, 64 * idx0 - len1, bits
    else:
        yield 0, 64 * (idx1 + 1) - len1, len1
        yield len1, 64 * idx0, len0


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


class _Array(Sequence):
    def __len__(self):
        return 4096


class BlockArray(_Array):
    def __init__(self, registry, data, palette, non_air=-1):
        self.registry = registry
        self.data = data
        self.bits = len(data) // 4096
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
            registry=registry,
            data=BitArray(length=4*4096),
            palette=[0],
            non_air=0 if count_non_air else None)

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
            registry,
            section.value["BlockStates"].value,
            proxy.palette)

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
        bits = length_to_bits(self.registry.max_bits, palette_len)
        if bits > 8:
            palette = []

        if self.bits == bits:
            # Nothing to do.
            return

        # Save contents
        values = self[:]

        # Update internals
        self.bits = bits
        self.data.clear()
        self.data.append(bits * 4096)
        self.palette.clear()
        self.palette.extend(palette)

        # Load contents
        self[:] = values

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[o] for o in xrange(*n.indices(4096))]
        if n >= 4096:
            raise IndexError(n)

        val = sum(self.data[pos:pos+length]
                  for _, pos, length in index_to_addresses(n, self.bits)).uint

        if self.palette:
            val = self.palette[val]

        return self.registry.decode_block(val)

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

        val = BitArray(uint=val, length=self.bits)
        for inpos, outpos, length in index_to_addresses(n, self.bits):
            self.data.overwrite(val[inpos:inpos+length], outpos)


class LightArray(_Array):
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
