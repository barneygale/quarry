import unittest
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
        print buff.unpack_blockposition()

if __name__ == '__main__':
    unittest.main()
