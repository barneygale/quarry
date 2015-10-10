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
.. autoclass:: quarry.net.server.ServerProtocol
    :members:
    :inherited-members:
    :exclude-members: makeConnection, logPrefix