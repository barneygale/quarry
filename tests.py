import unittest
from quarry.utils import types
from quarry.utils.buffer import Buffer, BufferUnderrun

class TestPackUnpack(unittest.TestCase):

    def testVarInt(self):
        value = 5533
        buff = Buffer()
        buff.buff = buff.pack_varint(value)
        self.assertTrue( buff.unpack_varint() == value )
        
    def testBlockPosition(self):
        blockpos = (345,-100,-2005)
        buff = Buffer()
        buff.buff = buff.pack_blockposition(blockpos)
        self.assertTrue(blockpos == buff.unpack_blockposition())

    def testChat(self):
        text = "Hi there !"
        buff = Buffer()
        buff.buff = buff.pack_chat(text)
        self.assertTrue(text == buff.unpack_chat())

    def testString(self):
        text = "more tests, and stuff"

        buff = Buffer()
        buff.buff = buff.pack_string(text)
        self.assertTrue(text == buff.unpack_string())

    def testUuid(self):
        uuid = types.UUID.from_offline_player("KLonter")
        buff = Buffer()
        buff.buff = buff.pack_uuid(uuid) 
        self.assertTrue(uuid == buff.unpack_uuid())



if __name__ == '__main__':
    unittest.main()
