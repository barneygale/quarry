Quarry: a Minecraft protocol library
====================================

|pypi| |travis_ci|

Quarry is a Python library that implements the `Minecraft protocol`_. It allows
you to write special purpose clients, servers and proxies.

Installation
------------

Use ``pip`` to install quarry:

.. code-block:: console

    $ pip install quarry

Features
--------

- Supports Minecraft 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, and 1.12.1
- Supports Python 2.7 and 3.3+
- Built upon ``twisted`` and ``cryptography``
- Exposes base classes and hooks for implementing your own client, server or
  proxy.
- Implements the design of the protocol - packet headers, modes, compression,
  encryption, login/session, etc.
- Implements all packets in "init", "status" and "login" modes
- Does *not* implement most packets in "play" mode - it is left up to you to
  hook and implement the packets you're interested in.

.. _Minecraft protocol: http://wiki.vg/Protocol

.. |pypi| image:: https://badge.fury.io/py/quarry.svg
    :target: https://pypi.python.org/pypi/quarry
    :alt: Latest version released on PyPi

.. |travis_ci| image:: https://travis-ci.org/barneygale/quarry.svg?branch=master
    :target: https://travis-ci.org/barneygale/quarry
    :alt: Travis CI current build results
