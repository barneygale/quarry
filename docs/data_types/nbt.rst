NBT
===

.. module:: quarry.utils.nbt

Quarry implements the Named Binary Tag (NBT) format. The following tag types
are available from the :mod:`quarry.utils.nbt` module:

.. list-table::
    :header-rows: 1

    - * Class
      * Value type
    - * ``TagByte``
      * ``int``
    - * ``TagShort``
      * ``int``
    - * ``TagInt``
      * ``int``
    - * ``TagLong``
      * ``int``
    - * ``TagFloat``
      * ``float``
    - * ``TagDouble``
      * ``float``
    - * ``TagByteArray``
      * ``list`` of ``int``
    - * ``TagIntArray``
      * ``list`` of ``int``
    - * ``TagList``
      * ``list`` of tags.
    - * ``TagCompound``
      * ``dict`` of names and tags.
    - * ``TagRoot``
      * ``dict`` containing a single name and tag.

Unlike some other NBT libraries, a tag's name is stored by its *parent* -
either a ``TagRoot`` or a ``TagCompound``. A tag when considered alone is
always nameless.

Note that there is no ``TagEnd`` class, as this is considered an implementation
detail.

All tag types have the following attributes and methods:

.. classmethod:: Tag.from_buff(buff)

    Returns a tag object from data at the beginning of the supplied
    :class:`~quarry.utils.buffer.Buffer` object.

.. method:: Tag.to_obj

    Returns a friendly representation of the tag using only basic Python
    datatypes. This is a lossy operation, as Python has fewer data types than
    NBT.

.. method:: Tag.to_bytes

    Returns a packed version of the tag as a byte string.

.. attribute:: Tag.value

    The value of the tag.

.. currentmodule:: quarry.utils.buffer

When working with NBT in relation to a :class:`~quarry.net.protocol.Protocol`,
the :meth:`Buffer.unpack_nbt` and :meth:`Buffer.pack_nbt` methods may be
helpful.