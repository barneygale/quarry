import base64
import re
import typing
from datetime import datetime


def str_bytes(string) -> bytes:
    if isinstance(string, str):
        return bytes(string, encoding="UTF-8")
    elif isinstance(string, bytes):
        return string
    raise ValueError(f"str_bytes expected str or bytes, got {type(string)}")


def bytes_str(byte_s) -> str:
    if isinstance(byte_s, str):
        return byte_s
    elif isinstance(byte_s, bytes):
        return byte_s.decode(encoding="UTF-8")
    raise ValueError(f"bytes_str expected str or bytes, got {type(byte_s)}")


class CertificatePair(object):
    BytesOrStr = typing.Union[str, bytes]

    def __init__(
        self,
        private: BytesOrStr,
        public: BytesOrStr,
        signature1: BytesOrStr,
        signature2: BytesOrStr,
        expires: str
    ):
        self.private = str_bytes(private)
        self.public = str_bytes(public)
        self.signature1 = str_bytes(signature1)
        self.signature2 = str_bytes(signature2)

        # ISO 8601, datetime really doesn't like extra fractional second precision

        # Capture up to 6 digits of fractional seconds, or none at all
        expires = re.sub(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)\d+(Z|\+[\d:]+)$', r'\1\2', expires)
        self.expires = datetime.strptime(expires, '%Y-%m-%dT%H:%M:%S.%f%z')  # cpython issue #80010

    def is_expired(self):
        return datetime.now() > self.expires

    def __eq__(self, other):
        if not isinstance(other, CertificatePair):
            return False
        return (
            self.private == other.private
            and self.public == other.public
            and self.signature1 == other.signature1
            and self.signature2 == other.signature2
            and self.expires == other.expires
        )

    def __lt__(self, other):
        if not isinstance(other, CertificatePair):
            return False
        return self.expires < other.expires

    def __gt__(self, other):
        if not isinstance(other, CertificatePair):
            return False
        return self.expires > other.expires

    def __le__(self, other):
        if not isinstance(other, CertificatePair):
            return False
        return self.expires <= other.expires

    def __ge__(self, other):
        if not isinstance(other, CertificatePair):
            return False
        return self.expires >= other.expires

    def __repr__(self):
        return f"{type(self).__name__}(pub={self.public[:16]}, s1={self.signature1[:16]}, s2={self.signature2[:16]}, expire={self.expires.isoformat()})"

    @classmethod
    def convert_public_key(cls, cert_pem):

        contents = r'-{3,}BEGIN[ A-Z]*-{3,}\n?((?:[a-zA-Z0-9/+]*\n?)*)-{3,}END[ A-Z]*-{3,}'
        contents = re.search(contents, bytes_str(cert_pem))
        if contents is None:
            raise ValueError("Invalid certificate (failed to parse)")
        contents = contents.group(1)
        contents = re.sub(r'\s', '', contents)
        ba = base64.b64decode(contents)
        return ba

    @classmethod
    def from_dict(cls, certificates):
        return cls(**certificates)

    def to_dict(self):
        return {
            "private": self.private,
            "public": self.public,
            "signature1": self.signature1,
            "signature2": self.signature2,
            "expires": self.expires.isoformat()
        }
