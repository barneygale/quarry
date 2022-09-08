import base64
import os
import sys
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import ciphers, serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers import algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from quarry.net.auth import PlayerPublicKey

backend = default_backend()

PY3 = sys.version_info > (3,)
_yggdrasil_key = None

class Cipher(object):
    def __init__(self):
        self.disable()

    def enable(self, key):
        cipher = ciphers.Cipher(
            algorithms.AES(key), modes.CFB8(key), backend=backend)
        self.encryptor = cipher.encryptor()
        self.decryptor = cipher.decryptor()

    def disable(self):
        self.encryptor = None
        self.decryptor = None

    def encrypt(self, data):
        if self.encryptor:
            return self.encryptor.update(data)
        else:
            return data

    def decrypt(self, data):
        if self.decryptor:
            return self.decryptor.update(data)
        else:
            return data


def make_keypair():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend())


def make_server_id():
    data = os.urandom(10)
    if PY3:
        parts = ["%02x" % c for c in data]
    else:
        parts = ["%02x" % ord(c) for c in data]

    return "".join(parts)


def make_verify_token():
    return os.urandom(4)


def make_shared_secret():
    return os.urandom(16)


def make_digest(*data):
    sha1 = hashlib.sha1()
    for d in data:
        sha1.update(d)

    digest = int(sha1.hexdigest(), 16)
    if digest >> 39*4 & 0x8:
        return"-%x" % ((-digest) & (2**(40*4)-1))
    else:
        return "%x" % digest


def export_public_key(keypair):
    return keypair.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)


def import_public_key(data):
    return serialization.load_der_public_key(
        data=data,
        backend=default_backend())


def encrypt_secret(public_key, shared_secret):
    return public_key.encrypt(
        plaintext=shared_secret,
        padding=padding.PKCS1v15())


def decrypt_secret(keypair, data):
    return keypair.decrypt(
        ciphertext=data,
        padding=padding.PKCS1v15())


def get_yggdrasil_session_key():
    global _yggdrasil_key

    if _yggdrasil_key is not None:
        return _yggdrasil_key

    yggdrasil_key_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "keys",
            "yggdrasil_session_pubkey.der"))
    yggdrasil_key_file = open(yggdrasil_key_path, "rb")
    _yggdrasil_key = import_public_key(yggdrasil_key_file.read())

    return _yggdrasil_key


# Verify 1.19 signature
def verify_mojang_v1_signature(data: PlayerPublicKey):
    # Need key in PEM format
    key_text = base64.encodebytes(data.key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).decode('ISO-8859-1')
    e = "-----BEGIN RSA PUBLIC KEY-----\n" + key_text + "-----END RSA PUBLIC KEY-----\n"

    try:
        # Signature is timestamp as string + public key in PEM format
        get_yggdrasil_session_key().verify(data.signature, bytes(str(data.expiry) + e, 'ascii'), PKCS1v15(), SHA1())
        return True
    except InvalidSignature:
        return False


# Verify 1.19.1+ signature
def verify_mojang_v2_signature(data: PlayerPublicKey, uuid):
    if uuid is None:
        return False

    try:
        # Signature is uuid bytes + timestamp bytes + public key bytes
        key_bytes = data.key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
        get_yggdrasil_session_key()\
            .verify(data.signature, uuid.bytes + data.expiry.to_bytes(8, 'big') + key_bytes, PKCS1v15(), SHA1())
        return True
    except InvalidSignature:
        return False
