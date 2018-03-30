from quarry.types.buffer.v1_7 import Buffer1_7


class Buffer1_9(Buffer1_7):

    # Pack/unpack entity metadata ---------------------------------------------

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
            if   ty == 0:  out += cls.pack('B', val)
            elif ty == 1:  out += cls.pack_varint(val)
            elif ty == 2:  out += cls.pack('f', val)
            elif ty == 3:  out += cls.pack_string(val)
            elif ty == 4:  out += cls.pack_chat(val)
            elif ty == 5:  out += cls.pack_slot(**val)
            elif ty == 6:  out += cls.pack('?', val)
            elif ty == 7:  out += cls.pack('fff', *val)
            elif ty == 8:  out += cls.pack_position(*val)
            elif ty == 9:  out += cls.pack_optional(pack_position, val)
            elif ty == 10: out += cls.pack_varint(val)
            elif ty == 11: out += cls.pack_optional(cls.pack_uuid, val)
            elif ty == 12: out += cls.pack_varint(val)
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
            if   ty == 0:  val = self.unpack('B')
            elif ty == 1:  val = self.unpack_varint()
            elif ty == 2:  val = self.unpack('f')
            elif ty == 3:  val = self.unpack_string()
            elif ty == 4:  val = self.unpack_chat()
            elif ty == 5:  val = self.unpack_slot()
            elif ty == 6:  val = self.unpack('?')
            elif ty == 7:  val = self.unpack('fff')
            elif ty == 8:  val = self.unpack_position()
            elif ty == 9:  val = self.unpack_optional(self.unpack_position)
            elif ty == 10: val = self.unpack_varint()
            elif ty == 11: val = self.unpack_optional(self.unpack_uuid)
            elif ty == 12: val = self.unpack_varint()
            elif ty == 13: val = self.unpack_nbt()
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata[ty, key] = val
