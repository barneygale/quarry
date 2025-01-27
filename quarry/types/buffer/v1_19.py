from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from quarry.net.auth import PlayerPublicKey
from quarry.net.crypto import import_public_key
from quarry.types.buffer.v1_14 import Buffer1_14


class Buffer1_19(Buffer1_14):

    @classmethod
    def pack_global_position(cls, dimension, x, y, z):
        """
        Packs a global position.
        """

        return cls.pack_string(dimension) + cls.pack_position(x, y, z)

    def unpack_global_position(self):
        """
        Unpacks a global position.
        """

        return self.unpack_string(), self.unpack_position()

    @classmethod
    def pack_entity_metadata(cls, metadata):
        """
        Packs entity metadata.
        """

        pack_position = lambda pos: cls.pack_position(*pos)
        pack_global_position = lambda pos: cls.pack_global_position(*pos)

        out = b""
        for ty_key, val in metadata.items():
            ty, key = ty_key
            out += cls.pack('B', key)
            out += cls.pack_varint(ty)

            if   ty == 0:  out += cls.pack('b', val)
            elif ty == 1:  out += cls.pack_varint(val)
            elif ty == 2:  out += cls.pack('f', val)
            elif ty == 3:  out += cls.pack_string(val)
            elif ty == 4:  out += cls.pack_chat(val)
            elif ty == 5:  out += cls.pack_optional(cls.pack_chat, val)
            elif ty == 6:  out += cls.pack_slot(**val)
            elif ty == 7:  out += cls.pack('?', val)
            elif ty == 8:  out += cls.pack_rotation(*val)
            elif ty == 9:  out += cls.pack_position(*val)
            elif ty == 10: out += cls.pack_optional(pack_position, val)
            elif ty == 11: out += cls.pack_direction(val)
            elif ty == 12: out += cls.pack_optional(cls.pack_uuid, val)
            elif ty == 13: out += cls.pack_block(val)
            elif ty == 14: out += cls.pack_nbt(val)
            elif ty == 15: out += cls.pack_particle(*val)
            elif ty == 16: out += cls.pack_villager(*val)
            elif ty == 17: out += cls.pack_optional_varint(val)
            elif ty == 18: out += cls.pack_pose(val)
            elif ty == 19: out += cls.pack_varint(val)
            elif ty == 20: out += cls.pack_varint(val)
            elif ty == 21: out += cls.pack_optional(pack_global_position, val)
            elif ty == 22: out += cls.pack_varint(val)
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
            elif ty == 5:  val = self.unpack_optional(self.unpack_chat)
            elif ty == 6:  val = self.unpack_slot()
            elif ty == 7:  val = self.unpack('?')
            elif ty == 8:  val = self.unpack_rotation()
            elif ty == 9:  val = self.unpack_position()
            elif ty == 10: val = self.unpack_optional(self.unpack_position)
            elif ty == 11: val = self.unpack_direction()
            elif ty == 12: val = self.unpack_optional(self.unpack_uuid)
            elif ty == 13: val = self.unpack_block()
            elif ty == 14: val = self.unpack_nbt()
            elif ty == 15: val = self.unpack_particle()
            elif ty == 16: val = self.unpack_villager()
            elif ty == 17: val = self.unpack_optional_varint()
            elif ty == 18: val = self.unpack_pose()
            elif ty == 19: val = self.unpack_varint(val)
            elif ty == 20: val = self.unpack_varint(val)
            elif ty == 21: val = self.unpack_optional(self.unpack_global_position)
            elif ty == 22: val = self.unpack_varint(val)
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata[ty, key] = val

    @classmethod
    def pack_player_public_key(cls, data: PlayerPublicKey):
        return cls.pack('Q', data.expiry) \
               + cls.pack_byte_array(data.key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)) \
               + cls.pack_byte_array(data.signature)

    def unpack_player_public_key(self):
        expiry = self.unpack('Q')
        key_bytes = self.unpack_byte_array()
        signature = self.unpack_byte_array()

        return PlayerPublicKey(expiry, import_public_key(key_bytes), signature)
