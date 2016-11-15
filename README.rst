Quarry: a Minecraft protocol library
====================================

Quarry is a Python library that implements the `Minecraft protocol`_. It allows
you to write special purpose clients, servers and proxies.

Installation
------------

Use ``pip`` to install quarry:

.. code-block:: console

    $ pip install quarry

Features
--------

- Supports Minecraft 1.7, 1.8, 1.9, 1.10 and 1.11
- Supports Python 2.7 and 3.2+
- Built upon ``twisted`` and ``cryptography``
- Exposes base classes and hooks for implementing your own client, server or
  proxy.
- Implements the design of the protocol - packet headers, modes, compression,
  encryption, login/session, etc.
- Implements all packets in "init", "status" and "login" modes
- Does *not* implement most packets in "play" mode - it is left up to you to
  hook and implement the packets you're interested in.

.. _Minecraft protocol: http://wiki.vg/Protocol
