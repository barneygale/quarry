from collections import Sequence
import math


try:
    xrange
except NameError:
    xrange = range


class _Array(Sequence):
    def __len__(self):
        return 4096


class BlockArray(_Array):
    def __init__(self, block_map, data, bits, palette=None):
        self.block_map = block_map
        self.data = data
        self.bits = bits
        self.palette = palette

    @classmethod
    def empty(cls, block_map):
        """
        Creates an empty block array.
        """
        return cls(block_map, [0] * 256, 4, [0])

    def is_empty(self):
        """
        Checks if this block array is entirely air. You may wish to call
        ``repack()`` before this method to avoid false negatives.
        """
        if self.palette is not None:
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

            palette = self.palette
            palette_len = len(palette) + reserve

        # Compute new bits
        bits = int(math.ceil(math.log(palette_len, 2)))
        if bits <= 8:
            if bits < 4:
                bits = 4
        else:
            bits = self.block_map.max_bits
            palette = []

        if set(self.palette) == set(palette):
            # Nothing to do.
            return

        # Save contents
        values = self[:]

        # Update internals
        self.data[:] = [0] * (64 * bits)
        self.bits = bits
        self.palette.clear()
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

        val = self.data[idx0] >> off0
        val &= (1 << off1) - 1
        if idx0 != idx1:
            val |= self.data[idx1] << off1
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

        self.data[idx0] &= ~mask0
        self.data[idx0] |= (2 ** 64 - 1) & mask0 & (val << off0)
        if (self.data[idx0] & (1 << (64 - 1))) != 0:
            self.data[idx0] = self.data[idx0]  - (1 << 64)

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

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[o] for o in xrange(*n.indices(4096))]
        assert isinstance(n, int)
        idx, off = divmod(n, 2)
        if off == 0:
            return self.data[idx] & 0x0F
        else:
            return self.data[idx] >> 4

    def __setitem__(self, n, val):
        assert isinstance(n, int)
        idx, off = divmod(n, 2)
        if off == 0:
            val = (self.data[idx] & 0xF0) | val
        else:
            val = (self.data[idx] & 0x0F) | (val << 4)

        if val > 127:
            val -= 256
        self.data[idx] = val
