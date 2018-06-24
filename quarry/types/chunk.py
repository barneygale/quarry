from collections import Sequence, MutableSequence
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


class _NBTPaletteProxy(MutableSequence):
    def __init__(self, block_map):
        self.block_map = block_map
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

        block = self.block_map.decode_block(self.palette[n])
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

        self.palette[n] = self.block_map.encode_block(block)


class _Array(Sequence):
    def __len__(self):
        return 4096


class BlockArray(_Array):
    def __init__(self, block_map, data, bits, palette=None):
        self.block_map = block_map
        self.data = data
        self.bits = bits
        self.palette = palette or []

    @classmethod
    def empty(cls, block_map):
        """
        Creates an empty block array.
        """
        return cls(block_map, [0] * 256, 4, [0])

    @classmethod
    def from_nbt(cls, section, block_map):
        """
        Creates a block array that uses the given NBT section tag as storage
        for block data and the palette. Minecraft 1.13+ only.
        """

        # Set up palette proxy
        nbt_palette = section.value['Palette']
        if isinstance(nbt_palette.value, _NBTPaletteProxy):
            proxy = nbt_palette.value
        else:
            proxy = _NBTPaletteProxy(block_map)
            for entry in nbt_palette.value:
                proxy.append(entry)
            nbt_palette.value = proxy

        # Load block data
        return cls(
            block_map,
            section.value["BlockStates"].value,
            length_to_bits(block_map.max_bits, len(proxy)),
            proxy.palette)

    def is_empty(self):
        """
        Checks if this block array is entirely air. You may wish to call
        ``repack()`` before this method to avoid false negatives.
        """
        if self.palette:
            return self.palette == [0]
        else:
            return not any(self.data)

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
            palette = [self.block_map.encode_block(block) for block in palette]
            palette_len = len(palette)
        else:
            if not self.palette:
                # Reserving space in an unpaletted array is a no-op.
                return

            palette = self.palette[:]
            palette_len = len(palette) + reserve

        # Compute new bits
        bits = length_to_bits(self.block_map.max_bits, palette_len)
        if bits > 8:
            palette = []

        if self.bits == bits:
            # Nothing to do.
            return

        # Save contents
        values = self[:]

        # Update internals
        self.data[:] = [0] * (64 * bits)
        self.bits = bits
        del self.palette[:]
        self.palette.extend(palette)

        # Load contents
        self[:] = values

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[o] for o in xrange(*n.indices(4096))]

        idx0 = (self.bits * n) // 64
        idx1 = (self.bits * (n + 1) - 1) // 64

        off0 = (self.bits * n) % 64
        off1 = 64 - off0

        if idx0 == idx1:
            val = self.data[idx0] >> off0
        else:
            val = (self.data[idx0] >> off0) | (self.data[idx1] << off1)

        val &= (1 << self.bits) - 1

        if self.palette:
            val = self.palette[val]

        return self.block_map.decode_block(int(val))

    def __setitem__(self, n, val):
        if isinstance(n, slice):
            for o in xrange(*n.indices(4096)):
                self[o] = val[o]
            return

        val = self.block_map.encode_block(val)

        if self.palette:
            try:
                val = self.palette.index(val)
            except ValueError:
                self.repack(reserve=1)

                if self.palette:
                    self.palette.append(val)
                    val = len(self.palette) - 1

        idx0 = (self.bits * n) // 64
        idx1 = (self.bits * (n + 1) - 1) // 64

        off0 = (self.bits * n) % 64
        off1 = 64 - off0

        mask0 = ((1 << self.bits) - 1) << off0
        mask1 = ((1 << self.bits) - 1) >> off1

        self.data[idx0] &= (2 ** 64 - 1) & ~mask0
        self.data[idx0] |= (2 ** 64 - 1) & mask0 & (val << off0)

        if idx0 != idx1:
            self.data[idx1] &= ~mask1
            self.data[idx1] |= mask1 & (val >> off1)


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
