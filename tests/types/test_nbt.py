# -*- coding: utf-8 -*-
import gzip
import os.path
from quarry.types.nbt import *
TagCompound.preserve_order = True # for testing purposes.


bigtest_path = os.path.join(os.path.dirname(__file__), "bigtest.nbt")

bigtest_alt_repr = """
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
    'Level': {
        'nested compound test': {
            'egg': {'name': 'Eggbert', 'value': 0.5},
            'ham': {'name': 'Hampus', 'value': 0.75}},
        'intTest': 2147483647,
        'byteTest': 127,
        'stringTest': 'HELLO WORLD THIS IS A TEST STRING \xc5\xc4\xd6!',
        'listTest (long)': [11, 12, 13, 14, 15],
        'doubleTest': 0.4931287132182315,
        'floatTest': 0.4982314705848694,
        'longTest': 9223372036854775807,
        'listTest (compound)': [
            {'created-on': 1264099775885, 'name': 'Compound tag #0'},
            {'created-on': 1264099775885, 'name': 'Compound tag #1'}],
        'byteArrayTest (the first 1000 values of (n*n*255+n*7)%100, starting with n=0 (0, 62, 34, 16, 8, ...))': \
            [(n*n*255+n*7)%100 for n in range(1000)],
        'shortTest': 32767}}


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
    bigtest = TagRoot({"Level": TagCompound({
        "byteTest": TagByte(127),
        "shortTest": TagShort(32767),
        "intTest": TagInt(2147483647),
        "longTest": TagLong(9223372036854775807),
        "floatTest": TagFloat(0.4982314705848694),
        "doubleTest": TagDouble(0.4931287132182315),
        "stringTest": TagString('HELLO WORLD THIS IS A TEST STRING \xc5\xc4\xd6!'),
        "byteArrayTest (the first 1000 values of (n*n*255+n*7)%100, starting "
        "with n=0 (0, 62, 34, 16, 8, ...))": \
            TagByteArray([(n*n*255+n*7)%100 for n in range(1000)]),
        "listTest (long)": TagList([TagLong(n) for n in range(11, 16)]),
        "listTest (compound)": TagList([
            TagCompound({"name": TagString("Compound tag #0"), "created-on": TagLong(1264099775885)}),
            TagCompound({"name": TagString("Compound tag #1"), "created-on": TagLong(1264099775885)})]),
        "nested compound test": TagCompound({
            "ham": TagCompound({
                "name": TagString("Hampus"),
                "value": TagFloat(0.75)}),
            "egg": TagCompound({
                "name": TagString("Eggbert"),
                "value": TagFloat(0.5)})})})})
    assert bigtest.to_obj() == bigtest_to_obj
