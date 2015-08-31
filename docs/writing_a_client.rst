Writing a Client
================

Skeleton client
---------------

To write a client, subclass :class:`ClientFactory` and
:class:`ClientProtocol`::

    from quarry.net.client import ClientProtocol

    class ExampleClientProtocol(ClientProtocol):
        pass

    class ExampleClientFactory(ClientFactory):
        protocol = ExampleClientProtocol

Logging in
----------

If you only need to log into offline-mode servers, you can create an offline
profile::

    from quarry.mojang.profile import Profile

    profile = Profile()
    profile.login_offline("Notch")

    factory = ExampleClientFactory()
    factory.profile = profile
    factory.connect("localhost", 25565)
    factory.run()

To log into online-mode servers, we need to talk to the Mojang session servers.
Quarry uses twisted_ under the hood, where instead of waiting for I/O to
complete, we register a callback that will be fired when login is complete::

    from quarry.mojang.profile import Profile

    profile = Profile()

    factory = ExampleClientFactory()
    factory.profile = profile

    def login_ok(data):
        factory.connect("localhost", 25565)

    def login_failed(err):
        print("login failed:", err.value)
        factory.stop()

    deferred = profile.login("someone@somewhere.com", "p4ssw0rd")
    deferred.addCallbacks(login_ok, login_failed)
    factory.run()

API Reference
-------------

Quarry's default packet handlers call certain methods when events occur. You
might want to call ``super()`` for these methods if you reimplement them.

.. class:: ClientProtocol()

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

        Called when we join the game. If the server is in online mode, this
        means the server accepted our session.

    .. method:: player_left(self):

        Called when we leave the game.

    .. method:: auth_ok(self, data):

        Called if the Mojang session server responds to our query. Note that
        this method does not indicate that the server accepted our session; in
        this case :meth:`player_joined` is called.

    .. method:: auth_failed(self, err):

        Called if the Mojang session server does not respond to our auth query
        or responds with an error.

    .. method:: status_response(self, data):

        If we're connecting in "status" mode, this is called when the server
        sends us information about itself.

.. _twisted: https://twistedmatrix.com