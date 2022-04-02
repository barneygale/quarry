from quarry.types.uuid import UUID

hex_vector = "b50ad385-829d-3141-a216-7e7d7539ba7f"
bytes_vector = b"\xb5\x0a\xd3\x85\x82\x9d\x31\x41" \
               b"\xa2\x16\x7e\x7d\x75\x39\xba\x7f"


def test_uuid_from_hex_to_byte():
    uuid = UUID.from_hex(hex_vector)
    assert isinstance(uuid, UUID)
    assert uuid.to_bytes() == bytes_vector


def test_uuid_from_bytes_to_hex():
    uuid = UUID.from_bytes(bytes_vector)
    assert isinstance(uuid, UUID)
    assert uuid.to_hex() == hex_vector
    assert uuid.to_hex(False) == hex_vector.replace("-", "")


def test_uuid_from_offline_player():
    uuid = UUID.from_offline_player("Notch")
    assert isinstance(uuid, UUID)
    assert uuid.to_bytes() == bytes_vector
