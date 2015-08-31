Writing a Server
================

Skeleton server
---------------

To write a server, subclass :class:`ServerFactory` and
:class:`ServerProtocol`::


    from quarry.net.server import ServerProtocol

    class ExampleServerProtocol(ServerProtocol):
        pass

    class ExampleServerFactory(ClientFactory):
        protocol = ExampleServerProtocol

API Reference
-------------

.. class:: ServerProtocol()

    .. attribute:: buff_type

        A reference to the :class:`Buffer` class. This is useful when
        constructing a packet payload for use in :meth:`send_packet`.

    .. attribute:: logger

        A reference to the logger.

    .. attribute:: tasks

        A reference to a :class:`Tasks` instance. This object has methods for
        setting up repeating or delayed callbacks.

    .. attribute:: remote_addr

        The remote endpoint's address. Use ``.host`` and ``.port`` to retrieve
        the IP address and port.

    .. method:: connection_made(self)

        Called when the connection is made.

    .. method:: connection_lost(self)

        Called when the connection is lost.

    .. method:: connection_timed_out(self)

        Called when the connection has been idle too long.

    .. method:: packet_received(self, name, buff)

        Called when a packet is received from the remote. Usually this method
        dispatches the packet to a method named ``packet_<packet name>``, or
        calls :meth:`packet_unhandled` if no such methods exists. You might
        want to override this to implement your own dispatch logic or logging.

    .. method:: packet_unhandled(self, name, buff)

        Called when a packet is received that is not hooked. The default
        implementation silently discards the packet.

    .. method:: send_packet(self, name, data=b"")

        Call this to send a packet to the remote.

    .. method:: player_joined(self):

        Called when the player joins the game.

    .. method:: player_left(self):

        Called when the player leaves the game.

    .. method:: auth_ok(self, data):

        Called if the Mojang session server confirms that the connecting client
        owns the username they claim to.

    .. method:: auth_failed(self, err):

        Called if the Mojang session server does not respond to our auth query
        or responds with an error.