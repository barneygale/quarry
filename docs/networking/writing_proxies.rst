Writing a Proxy
===============


.. currentmodule:: quarry.net.proxy

A quarry proxy has five main parts:

.. list-table::

    - * Class
      * Superclass
      * Description

    - * :class:`DownstreamFactory`
      * :class:`~quarry.net.server.ServerFactory`
      * Spawns ``Downstream`` objects for connecting clients
    - * ``Downstream``
      * :class:`~quarry.net.server.ServerProtocol`
      * Connection with an external client
    - * :class:`Bridge`
      * ``PacketDispatcher``
      * Forwards packets between the up/downstream
    - * ``UpstreamFactory``
      * :class:`~quarry.net.client.ClientFactory`
      * Spawns an ``Upstream``
    - * ``Upstream``
      * :class:`~quarry.net.client.ClientProtocol`
      * Connection with an external server

In ASCII art::

    +--------+       +--------------------------------+       +--------+
    | mojang | ----> |              QUARRY            | ----> | mojang |
    | client | <---- | downstream | bridge | upstream | <---- | server |
    +--------+       +--------------------------------+       +--------+

Typically the :class:`Bridge` and :class:`DownstreamFactory` are
customized.

When the user connects, the :class:`DownstreamFactory` creates a
``Downstream`` object to communicate with the external client. If we're running
in online-mode, we go through server-side auth with mojang.

Once the user is authed, we spawn a ``UpstreamFactory``, which makes a
connection to the external server and spawns an ``Upstream`` to handle it.
If requested we go through client-side auth.

At this point both endpoints of the proxy are authenticated and switched to
"play" mode. The :class:`Bridge` assumes responsibility for passing packets
between the endpoints. Proxy business logic is typically implemented by
defining packet handlers in a :class:`Bridge` subclass, much like in client and
server :doc:`protocols <factories_protocols>`. Unlike clients and servers, the
method name must include the packet direction before its name, e.g.:

.. code-block:: python

    # Hook server-to-client keep alive
    def packet_upstream_tab_complete(self, buff):
        # Unpack the packet
        p_text = buff.unpack_string()

        # Do a custom thing
        if p_text.startswith("/msg"):
            return # Drop the packet

        # Forward the packet
        buff.restore()
        self.upstream.send_packet("tab_complete", buff.read())

If a packet is hooked but not explicitly forwarded it is effectively dropped.
Unhooked packets are handled by :meth:`Bridge.packet_unhandled`, which
forwards packets by default.


Skeleton Proxy
--------------

The proxy below will do online-mode authentication with a client connecting on
port 25565, then connect in offline mode to a server running on port 25566
and begin exchanging packets via the bridge.

.. code-block:: python

    from twisted.internet import reactor
    from quarry.net.proxy import DownstreamFactory, Bridge


    class ExampleBridge(Bridge):
        pass


    def main(argv):
        factory = DownstreamFactory()
        factory.bridge_class = ExampleBridge
        factory.connect_host = "127.0.0.1"
        factory.connect_port = 25566
        factory.listen("127.0.0.1", 25565)
        reactor.run()


    if __name__ == "__main__":
        import sys
        main(sys.argv[1:])

Downstream Factories
--------------------

.. autoclass:: DownstreamFactory

    Subclass of :class:`quarry.net.server.ServerFactory`. Additional
    attributes:

    .. autoattribute:: bridge_class
    .. autoattribute:: connect_host
    .. autoattribute:: connect_port


Bridges
-------

.. autoclass:: Bridge

    .. autoattribute:: upstream_factory_class
    .. autoattribute:: log_level

    .. autoattribute:: logger
    .. autoattribute:: downstream_factory
    .. autoattribute:: downstream
    .. autoattribute:: upstream_profile
    .. autoattribute:: upstream_factory
    .. autoattribute:: upstream

    .. automethod:: make_profile
    .. automethod:: connect

    .. automethod:: downstream_ready
    .. automethod:: upstream_ready
    .. automethod:: downstream_disconnected
    .. automethod:: upstream_disconnected

    .. automethod:: enable_forwarding
    .. automethod:: enable_fast_forwarding

    .. automethod:: packet_received
    .. automethod:: packet_unhandled
