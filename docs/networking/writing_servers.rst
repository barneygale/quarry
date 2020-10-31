Writing a Server
================

.. currentmodule:: quarry.net.server

A server is generally made up of two parts:

- A subclass of :class:`ServerFactory`. Under normal circumstances only one
  ``ServerFactory`` is instantiated. This object represents your game server
  as a whole.
- A subclass of :class:`ServerProtocol`. Each object represents a connection
  with a client.

.. seealso::
    :doc:`factories_protocols`


Skeleton Server
---------------

By default quarry takes clients through the authentication process and then
switches into the "play" protocol mode. Normally at this point you would
implement :meth:`~quarry.net.protocol.Protocol.player_joined` to either
disconnect the client or start the process of spawning the player. In the
skeleton server below we don't do either, which leaves the client on the
"Logging in..." screen. Please see the :doc:`/examples` for less pointless
servers.

.. code-block:: python

    from twisted.internet import reactor
    from quarry.net.server import ServerFactory, ServerProtocol

    class ExampleServerProtocol(ServerProtocol):
        pass

    class ExampleServerFactory(ServerFactory):
        protocol = ExampleServerProtocol


    factory = ExampleServerFactory()
    factory.listen('127.0.0.1', 25565)
    reactor.run()
