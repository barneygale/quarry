import functools
import json
import re
from typing import List

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256

from quarry.types.uuid import UUID


def _load_styles():
    data = {
        "0": "black",
        "1": "dark_blue",
        "2": "dark_green",
        "3": "dark_aqua",
        "4": "dark_red",
        "5": "dark_purple",
        "6": "gold",
        "7": "gray",
        "8": "dark_gray",
        "9": "blue",
        "a": "green",
        "b": "aqua",
        "c": "red",
        "d": "light_purple",
        "e": "yellow",
        "f": "white",
        "k": "obfuscated",
        "l": "bold",
        "m": "strikethrough",
        "n": "underline",
        "o": "italic",
        "r": "reset",
    }

    code_by_name = {}
    code_by_prop = {}
    for code, name in data.items():
        code_by_name[name] = code
        if code in "klmnor":
            if name == "underline":
                prop = "underlined"
            else:
                prop = name
            code_by_prop[prop] = code

    return code_by_name, code_by_prop


code_by_name, code_by_prop = _load_styles()


@functools.total_ordering
class Message(object):
    """
    Represents a Minecraft chat message.
    """
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_buff(cls, buff):
        return cls(buff.unpack_json())

    def to_bytes(self):
        from quarry.types.buffer import Buffer

        return Buffer.pack_json(self.value)

    @classmethod
    def from_string(cls, string):
        return cls({'text': string})

    def to_string(self, strip_styles=True):
        """
        Minecraft uses a JSON format to represent chat messages; this method
        retrieves a plaintext representation, optionally including styles
        encoded using old-school chat codes (U+00A7 plus one character).
        """

        def parse(obj):
            if isinstance(obj, str):
                return obj
            if isinstance(obj, list):
                return "".join((parse(e) for e in obj))
            if isinstance(obj, dict):
                text = ""
                for prop, code in code_by_prop.items():
                    if obj.get(prop):
                        text += "\u00a7" + code
                if "color" in obj:
                    text += "\u00a7" + code_by_name[obj["color"]]
                if "translate" in obj:
                    text += obj["translate"]
                    if "with" in obj:
                        args = ", ".join((parse(e) for e in obj["with"]))
                        text += "{%s}" % args
                if "text" in obj:
                    text += obj["text"]
                if "extra" in obj:
                    text += parse(obj["extra"])
                return text

        text = parse(self.value)
        if strip_styles:
            text = self.strip_chat_styles(text)
        return text

    @classmethod
    def strip_chat_styles(cls, text):
        return re.sub("\u00A7.", "", text)

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return "<Message %r>" % str(self)


class LastSeenMessage(object):
    def __init__(self, sender: UUID, signature=None):
        self.sender = sender
        self.signature = signature

    def __eq__(self, other):
        if isinstance(other, LastSeenMessage):
            return self.sender == other.sender and self.signature == other.signature
        return NotImplemented


class SignedMessageHeader(object):
    """
    Represents the header of a signed minecraft chat message sent from a 1.19+ client
    Includes the sender UUID and optional signature of the preceding message
    """

    def __init__(self, sender: UUID, previous_signature: bytes = None):
        self.sender = sender
        self.previous_signature = previous_signature

    def __eq__(self, other):
        if isinstance(other, SignedMessageHeader):
            return self.sender == other.sender and self.previous_signature == other.previous_signature
        elif isinstance(other, LastSeenMessage):
            return self.sender == other.sender and self.previous_signature == other.signature
        return NotImplemented


class SignedMessageBody(object):
    """
    Represents the body of a signed minecraft chat message sent from a 1.19+ client
    Includes the message content, optional decorated message, timestamp and salt
    """

    def __init__(self, message: str, timestamp: int, salt: int, decorated_message: Message = None,
                 last_seen: List[LastSeenMessage] = None):
        self.message = message
        self.decorated_message = decorated_message
        self.timestamp = timestamp
        self.salt = salt

        if last_seen is None:
            last_seen = []

        self.last_seen = last_seen

    def digest(self):
        digest = hashes.Hash(hashes.SHA256())

        digest.update(self.salt.to_bytes(8, 'big'))  # Salt
        digest.update(int(self.timestamp / 1000).to_bytes(8, 'big'))  # Timestamp in seconds
        digest.update(self.message.encode("utf-8"))  # Message bytes
        digest.update((70).to_bytes(1, 'big'))  # Mojang adds a 70 byte after the message for some reason?

        if self.decorated_message is not None:
            digest.update(self.decorated_message.value.encode("utf-8"))  # FIXME: Test this

        for entry in self.last_seen:
            digest.update((70).to_bytes(1, 'big'))  # Mojang adds a 70 byte before each entry for some reason?
            digest.update(entry.sender.bytes)
            digest.update(entry.signature)

        return digest.finalize()

    def __eq__(self, other):
        if isinstance(other, SignedMessageBody):
            return self.message == other.message \
                   and self.decorated_message == other.decorated_message \
                   and self.timestamp == other.timestamp \
                   and self.salt == other.salt
        return NotImplemented


class SignedMessage(object):
    """
    Represents a signed minecraft chat message sent from a 1.19+ client
    Includes:
     - The message header, containing the sender UUID and optionally the previous message's signature,
     - The message body, containing the signed message, optional signed decorated message, timestamp and salt
     - The message signature, which may not be valid and can be checked with verify()
     - Optional unsigned message content
    """

    def __init__(self, header: SignedMessageHeader, signature: bytes, signature_version: int, body: SignedMessageBody,
                 unsigned_content: Message = None):
        if signature_version < 759:
            raise Exception("Signed messages are not supported below protocol version 759")

        self.header = header
        self.signature = signature
        self.signature_version = signature_version
        self.body = body
        self.unsigned_content = unsigned_content

    def verify(self, key: RSAPublicKey):
        data = b''

        if key is None or self.header.sender is None:
            return False

        # 1.19.1 +
        if self.signature_version >= 760:
            if self.header.previous_signature is not None:
                data = data + self.header.previous_signature

            data = data + self.header.sender.bytes + self.body.digest()

        # 1.19
        else:
            data = data + self.body.salt.to_bytes(8, 'big') \
                   + self.header.sender.bytes \
                   + int(self.body.timestamp / 1000).to_bytes(8, 'big') \
                   + json.dumps(Message.from_string(self.body.message).value, sort_keys=True, separators=(',', ':')).encode('utf-8')

        try:
            key.verify(self.signature, data, PKCS1v15(), SHA256())
            return True
        except InvalidSignature:
            return False

    def __eq__(self, other):
        if isinstance(other, SignedMessage):
            return self.header == other.header \
                   and self.body == other.body \
                   and self.signature == other.signature \
                   and self.signature_version == other.signature_version \
                   and self.unsigned_content == other.unsigned_content
        return NotImplemented
