import uuid

class UUID(uuid.UUID):
    @classmethod
    def from_hex(cls, hex):
        return UUID(hex=hex)

    @classmethod
    def from_bytes(cls, bytes):
        return UUID(bytes=bytes)

    @classmethod
    def from_offline_player(cls, display_name):
        class FakeNamespace():
            bytes = b'OfflinePlayer:'
        base_uuid = uuid.uuid3(FakeNamespace(), display_name)
        return UUID(bytes=base_uuid.bytes)

    def to_hex(self, with_dashes=True):
        if with_dashes:
            return "%s" % self
        else:
            return self.hex

    def to_bytes(self):
        return self.bytes