Registry
========

.. currentmodule:: quarry.types.buffer

Quarry can be told to encode/decode block, item and other information by
setting the :attr:`~Buffer.registry` attribute on the in-use buffer. This can be
set directly or by deriving a subclass and customizing
:meth:`~quarry.net.client.ClientFactory.get_buff_type()`. The registry
affects the following methods:

- :meth:`~Buffer.unpack_slot()` and :meth:`~Buffer.pack_slot()`
- :meth:`~Buffer.unpack_block()` and :meth:`~Buffer.pack_block()`
- :meth:`~Buffer.unpack_entity_metadata()` and
  :meth:`~Buffer.pack_entity_metadata()`
- :meth:`~Buffer.unpack_chunk_section()` and
  :meth:`~Buffer.pack_chunk_section()`
- :meth:`~Buffer.unpack_villager()` and :meth:`~Buffer.pack_villager()`
- :meth:`~Buffer.unpack_particle()` and :meth:`~Buffer.pack_particle()`

.. module:: quarry.types.registry

All registry objects have the following methods:

.. automethod:: Registry.encode
.. automethod:: Registry.decode
.. automethod:: Registry.encode_block
.. automethod:: Registry.decode_block
.. automethod:: Registry.is_air_block

Quarry supports the following registry types:

.. autoclass:: OpaqueRegistry
.. autoclass:: BitShiftRegistry
.. autoclass:: LookupRegistry
    :members: from_jar, from_json
