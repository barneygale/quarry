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
      * ``list`` of :class:`NamedTag` objects.

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

.. currentmodule:: quarry.utils.nbt

Tag Naming
----------

Tag naming is implemented in the :class:`NamedTag` class. These objects have
``name`` and ``value`` attributes, where ``value`` refers to an underlying
"value tag" object, such as a ``TagByte``. They are encountered as children of
``TagCompound`` (``compound_tag.value`` is a list of named tags) and as the
top-level tag when reading NBT from the network or from a file (in these cases,
the name is always empty). In Notch's description of NBT, tags are either
*named* or *nameless*, and most NBT libraries implement this by giving all tags
an optional ``name`` attribute. In quarry's implementation, the naming of tags
is implemented by a :class:`NamedTag` object that sits between the underlying
tag and the ``TagCompound``. A tag when considered alone is always nameless.

.. class:: NamedTag

    .. attribute:: name

        The name of the tag that is stored in :attr:`value`.

    .. attribute:: value

        The tag being named.