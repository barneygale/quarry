from quarry.types.buffer.v1_7 import Buffer1_7
from quarry.types.chunk import PackedArray, BlockArray


# Python 3 compat
try:
    xrange
except NameError:
    xrange = range


class Buffer1_9(Buffer1_7):

    # Chunk section -----------------------------------------------------------

    @classmethod
    def pack_chunk(cls, sections):
        data = b""
        for section in sections:
            if section and not section[0].is_empty():
                data += cls.pack_chunk_section(*section)
        return data

    @classmethod
    def pack_chunk_bitmask(cls, sections):
        bitmask = 0
        for i, section in enumerate(sections):
            if section and not section[0].is_empty():
                bitmask |= 1 << i
        return cls.pack_varint(bitmask)

    @classmethod
    def pack_chunk_section(cls, blocks, block_lights, sky_lights=None):
        """
        Packs a chunk section. The supplied arguments should be instances of
        ``BlockArray`` and ``LightArray`` from ``quarry.types.chunk``.
        """

        out = cls.pack('B', blocks.storage.value_width)
        out += cls.pack_chunk_section_palette(blocks.palette)
        out += cls.pack_chunk_section_array(blocks.to_bytes())
        out += block_lights.to_bytes()
        if sky_lights:
            out += sky_lights.to_bytes()
        return out

    @classmethod
    def pack_chunk_section_palette(cls, palette):
        return cls.pack_varint(len(palette)) + b"".join(
            cls.pack_varint(x) for x in palette)

    @classmethod
    def pack_chunk_section_array(cls, data):
        return cls.pack_varint(len(data) // 8) + data

    def unpack_chunk(self, bitmask, overworld=True):
        sections = []
        for idx in range(16):
            if bitmask & (1 << idx):
                section = self.unpack_chunk_section(overworld)
            else:
                section = None
            sections.append(section)
        return sections

    def unpack_chunk_section(self, overworld=True):
        """
        Unpacks a chunk section. Returns a 3-tuple of
        ``(blocks, block_lights, sky_lights)``, where *sky_lights* is ``None``
        when *overworld* is ``False``. The returned values are sequences of
        length 4096 (16x16x16).
        """

        value_width = self.unpack('B')
        palette = self.unpack_chunk_section_palette(value_width)
        array = self.unpack_chunk_section_array(value_width)
        blocks = BlockArray.from_bytes(
            bytes=array,
            palette=palette,
            registry=self.registry,
            non_air=None,
            value_width=value_width)
        block_lights = PackedArray.from_light_bytes(self.read(2048))
        if overworld:
            sky_lights = PackedArray.from_light_bytes(self.read(2048))
        else:
            sky_lights = None

        return blocks, block_lights, sky_lights

    def unpack_chunk_section_palette(self, value_width):
        return [self.unpack_varint() for _ in xrange(self.unpack_varint())]

    def unpack_chunk_section_array(self, value_width):
        return self.read(self.unpack_varint() * 8)

    # Entity metadata ---------------------------------------------------------

    @classmethod
    def pack_entity_metadata(cls, metadata):
        """
        Packs entity metadata.
        """

        pack_position = lambda pos: cls.pack_position(*pos)
        out = b""
        for ty_key, val in metadata.items():
            ty, key = ty_key
            out += cls.pack('BB', key, ty)
            if   ty == 0:  out += cls.pack('b', val)
            elif ty == 1:  out += cls.pack_varint(val)
            elif ty == 2:  out += cls.pack('f', val)
            elif ty == 3:  out += cls.pack_string(val)
            elif ty == 4:  out += cls.pack_chat(val)
            elif ty == 5:  out += cls.pack_slot(**val)
            elif ty == 6:  out += cls.pack('?', val)
            elif ty == 7:  out += cls.pack_rotation(*val)
            elif ty == 8:  out += cls.pack_position(*val)
            elif ty == 9:  out += cls.pack_optional(pack_position, val)
            elif ty == 10: out += cls.pack_direction(val)
            elif ty == 11: out += cls.pack_optional(cls.pack_uuid, val)
            elif ty == 12: out += cls.pack_block(val)
            elif ty == 13: out += cls.pack_nbt(val)
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
        out += cls.pack('B', 255)
        return out

    def unpack_entity_metadata(self):
        """
        Unpacks entity metadata.
        """

        metadata = {}
        while True:
            key = self.unpack('B')
            if key == 255:
                return metadata
            ty = self.unpack('B')
            if   ty == 0:  val = self.unpack('b')
            elif ty == 1:  val = self.unpack_varint()
            elif ty == 2:  val = self.unpack('f')
            elif ty == 3:  val = self.unpack_string()
            elif ty == 4:  val = self.unpack_chat()
            elif ty == 5:  val = self.unpack_slot()
            elif ty == 6:  val = self.unpack('?')
            elif ty == 7:  val = self.unpack_rotation()
            elif ty == 8:  val = self.unpack_position()
            elif ty == 9:  val = self.unpack_optional(self.unpack_position)
            elif ty == 10: val = self.unpack_direction()
            elif ty == 11: val = self.unpack_optional(self.unpack_uuid)
            elif ty == 12: val = self.unpack_block()
            elif ty == 13: val = self.unpack_nbt()
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata[ty, key] = val
