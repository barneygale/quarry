from quarry.types.buffer.v1_13 import Buffer1_13


class Buffer1_13_2(Buffer1_13):
    @classmethod
    def pack_slot(cls, item=None, count=1, tag=None):
        """
        Packs a slot.
        """

        if item is None:
            return cls.pack('?', False)
        else:
            return cls.pack('?', True) + \
                   cls.pack_varint(cls.block_map.encode_item(item)) + \
                   cls.pack('b', count) + \
                   cls.pack_nbt(tag)

    def unpack_slot(self):
        """
        Unpacks a slot.
        """

        slot = {}
        item_id = self.unpack_optional(self.unpack_varint)
        if item_id is None:
            slot['item'] = None
        else:
            slot['item'] = self.block_map.decode_item(item_id)
            slot['count'] = self.unpack('b')
            slot['tag'] = self.unpack_nbt()
        return slot