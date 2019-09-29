# -*- coding: utf-8 -*-
import gzip
import os.path
from quarry.types.nbt import *
TagCompound.preserve_order = True # for testing purposes.


bigtest_path = os.path.join(os.path.dirname(__file__), "bigtest.nbt")

bigtest_alt_repr = u"""
TAG_Compound("Level"): 11 entries
{
  TAG_Long("longTest"): 9223372036854775807
  TAG_Short("shortTest"): 32767
  TAG_String("stringTest"): "HELLO WORLD THIS IS A TEST STRING ÅÄÖ!"
  TAG_Float("floatTest"): 0.4982314705848694
  TAG_Int("intTest"): 2147483647
  TAG_Compound("nested compound test"): 2 entries
  {
    TAG_Compound("ham"): 2 entries
    {
      TAG_String("name"): "Hampus"
      TAG_Float("value"): 0.75
    }
    TAG_Compound("egg"): 2 entries
    {
      TAG_String("name"): "Eggbert"
      TAG_Float("value"): 0.5
    }
  }
  TAG_List("listTest (long)"): 5 entries
  {
    TAG_Long: 11
    TAG_Long: 12
    TAG_Long: 13
    TAG_Long: 14
    TAG_Long: 15
  }
  TAG_List("listTest (compound)"): 2 entries
  {
    TAG_Compound: 2 entries
    {
      TAG_String("name"): "Compound tag #0"
      TAG_Long("created-on"): 1264099775885
    }
    TAG_Compound: 2 entries
    {
      TAG_String("name"): "Compound tag #1"
      TAG_Long("created-on"): 1264099775885
    }
  }
  TAG_Byte("byteTest"): 127
  TAG_ByteArray("byteArrayTest (the first 1000 values of (n*n*255+n*7)%100, starting with n=0 (0, 62, 34, 16, 8, ...))"): 1000 entries
  TAG_Double("doubleTest"): 0.4931287132182315
}
"""

bigtest_to_obj = {
    u'Level': {
        u'nested compound test': {
            u'egg': {u'name': u'Eggbert', u'value': 0.5},
            u'ham': {u'name': u'Hampus', u'value': 0.75}},
        u'intTest': 2147483647,
        u'byteTest': 127,
        u'stringTest': u'HELLO WORLD THIS IS A TEST STRING \xc5\xc4\xd6!',
        u'listTest (long)': [11, 12, 13, 14, 15],
        u'doubleTest': 0.4931287132182315,
        u'floatTest': 0.4982314705848694,
        u'longTest': 9223372036854775807,
        u'listTest (compound)': [
            {u'created-on': 1264099775885, u'name': u'Compound tag #0'},
            {u'created-on': 1264099775885, u'name': u'Compound tag #1'}],
        u'byteArrayTest (the first 1000 values of (n*n*255+n*7)%100, starting with n=0 (0, 62, 34, 16, 8, ...))': \
            [(n*n*255+n*7)%100 for n in range(1000)],
        u'shortTest': 32767}}


def test_bigtest_alt_repr():
    bigtest = NBTFile.load(bigtest_path).root_tag
    assert alt_repr(bigtest) == bigtest_alt_repr.strip()


def test_bigtest_to_obj():
    bigtest = NBTFile.load(bigtest_path).root_tag
    assert bigtest_to_obj == bigtest.to_obj()

def test_bigtest_unpack_pack():
    with gzip.open(bigtest_path) as fd:
        bigtest_data_before = fd.read()

    bigtest = NBTFile.load(bigtest_path).root_tag
    bigtest_data_after = bigtest.to_bytes()

    assert bigtest_data_before == bigtest_data_after

def test_manual_bigtest_to_obj():
    bigtest = TagRoot({u"Level": TagCompound({
        u"byteTest": TagByte(127),
        u"shortTest": TagShort(32767),
        u"intTest": TagInt(2147483647),
        u"longTest": TagLong(9223372036854775807),
        u"floatTest": TagFloat(0.4982314705848694),
        u"doubleTest": TagDouble(0.4931287132182315),
        u"stringTest": TagString(u'HELLO WORLD THIS IS A TEST STRING \xc5\xc4\xd6!'),
        u"byteArrayTest (the first 1000 values of (n*n*255+n*7)%100, starting "
        u"with n=0 (0, 62, 34, 16, 8, ...))": \
            TagByteArray([(n*n*255+n*7)%100 for n in range(1000)]),
        u"listTest (long)": TagList([TagLong(n) for n in range(11, 16)]),
        u"listTest (compound)": TagList([
            TagCompound({u"name": TagString(u"Compound tag #0"), u"created-on": TagLong(1264099775885)}),
            TagCompound({u"name": TagString(u"Compound tag #1"), u"created-on": TagLong(1264099775885)})]),
        u"nested compound test": TagCompound({
            u"ham": TagCompound({
                u"name": TagString(u"Hampus"),
                u"value": TagFloat(0.75)}),
            u"egg": TagCompound({
                u"name": TagString(u"Eggbert"),
                u"value": TagFloat(0.5)})})})})
    assert bigtest.to_obj() == bigtest_to_obj
