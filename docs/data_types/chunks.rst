Chunks
======

.. module:: quarry.types.chunk

Quarry implements the `Chunk Section`_ data type used in `Chunk Data`_ packets.
This format consists of:

* A tightly-packed array of blocks using 4-8 or 13 bits per block, usually
  employing a palette.
* A tightly-packed array of light using 4 bits per block.

These types are implemented through the :class:`BlockArray` and
:class:`LightArray` classes. Each is a sequence containing exactly 4096 values
(16x16x16) and supporting the usual sequence operations (iteration, get/set
values, etc).

.. currentmodule:: quarry.types.buffer

On the client side, call :meth:`Buffer.unpack_chunk()` to retrieve a tuple
of block data, block light and (if *overworld* is ``True``) sky light.

On the server side, call :meth:`Buffer.pack_chunk()`, passing in block data,
block light and either sky light or ``None``.

.. currentmodule:: quarry.types.chunk

.. autoclass:: BlockArray
    :undoc-members:
    :members:


.. autoclass:: LightArray
    :undoc-members:
    :members:


.. _Chunk Section: http://wiki.vg/SMP_Map_Format
.. _Chunk Data: http://wiki.vg/Protocol#Chunk_Data