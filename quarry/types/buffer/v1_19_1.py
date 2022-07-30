from typing import List

from quarry.types.buffer.v1_19 import Buffer1_19
from quarry.types.chat import LastSeenMessage, SignedMessage, SignedMessageHeader, SignedMessageBody


class Buffer1_19_1(Buffer1_19):
    @classmethod
    def pack_last_seen_list(cls, entries: List[LastSeenMessage]):
        packed = cls.pack_varint(len(entries))

        if len(entries) > 5:
            from quarry.net.protocol import ProtocolError
            raise ProtocolError("Last seen list is too large")

        for entry in entries:
            packed = packed + cls.pack_last_seen_entry(entry)

        return packed

    def unpack_last_seen_list(self):
        seen_messages = []
        seen_messages_length = self.unpack_varint()

        if seen_messages_length > 5:
            from quarry.net.protocol import ProtocolError
            raise ProtocolError("Last seen list is too large")

        for i in range(seen_messages_length):
            seen_messages.append(self.unpack_last_seen_entry())

        return seen_messages

    @classmethod
    def pack_last_seen_entry(cls, entry: LastSeenMessage):
        return cls.pack_uuid(entry.sender) + cls.pack_byte_array(entry.signature)

    def unpack_last_seen_entry(self):
        return LastSeenMessage(self.unpack_uuid(), self.unpack_byte_array())

    @classmethod
    def pack_last_received(cls, entry: LastSeenMessage):
        return cls.pack_optional(cls.pack_last_seen_entry, entry)

    def unpack_last_received(self):
        return self.unpack_optional(self.unpack_last_seen_entry)

    @classmethod
    def pack_signed_message(cls, message: SignedMessage):
        return cls.pack_optional(cls.pack_byte_array, message.header.previous_signature) \
               + cls.pack_uuid(message.header.sender) \
               + cls.pack_byte_array(message.signature or b'') \
               + cls.pack_string(message.body.message) \
               + cls.pack_optional(cls.pack_chat, message.body.decorated_message) \
               + cls.pack('QQ', message.body.timestamp, message.body.salt) \
               + cls.pack_last_seen_list(message.body.last_seen) \
               + cls.pack_optional(cls.pack_chat, message.unsigned_content)

    def unpack_signed_message(self):
        previous_signature = self.unpack_optional(self.unpack_byte_array)
        uuid = self.unpack_uuid()
        signature = self.unpack_byte_array()
        message = self.unpack_string()
        decorated_message = self.unpack_optional(self.unpack_chat)
        timestamp = self.unpack('Q')
        salt = self.unpack('Q')
        last_seen = self.unpack_last_seen_list()
        unsigned_content = self.unpack_optional(self.unpack_chat)

        header = SignedMessageHeader(uuid, previous_signature)
        body = SignedMessageBody(message, timestamp, salt, decorated_message, last_seen)
        return SignedMessage(header, signature, 760, body, unsigned_content)
