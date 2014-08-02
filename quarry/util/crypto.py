from twisted.web.client import HTTPClientFactory
HTTPClientFactory.noisy = False

from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

import hashlib


class Cipher:
    def __init__(self):
        self.disable()

    def enable(self, key):
        self.encrypt = AES.new(key, AES.MODE_CFB, key).encrypt
        self.decrypt = AES.new(key, AES.MODE_CFB, key).decrypt

    def disable(self):
        self.encrypt = lambda d: d
        self.decrypt = lambda d: d


def make_keypair():
    return RSA.generate(1024)

def make_server_id():
    return "".join("%02x" % ord(c) for c in get_random_bytes(10))

def make_verify_token():
    return get_random_bytes(4)

def make_shared_secret():
    return get_random_bytes(16)

def make_digest(*data):
    sha1 = hashlib.sha1()
    for d in data: sha1.update(d)

    digest = long(sha1.hexdigest(), 16)
    if digest >> 39*4 & 0x8:
        return"-%x" % ((-digest) & (2**(40*4)-1))
    else:
        return "%x" % digest

def export_public_key(keypair):
    return keypair.publickey().exportKey(format="DER")

def import_public_key(data):
    return RSA.importKey(data)

def _pkcs1_unpad(data):
    pos = data.find('\x00')
    if pos > 0:
        return data[pos+1:]

def _pkcs1_pad(data):
    assert len(data) < 117
    padding = ""
    while len(padding) < 125-len(data):
        byte = get_random_bytes(1)
        if byte != '\x00':
            padding += byte
    return '\x00\x02%s\x00%s' % (padding, data)

def encrypt_secret(public_key, shared_secret):
    d = _pkcs1_pad(shared_secret)
    return public_key.encrypt(d, 0)[0]

def decrypt_secret(keypair, data):
    return _pkcs1_unpad(keypair.decrypt(data))