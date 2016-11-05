Writing a Client
================

.. module:: quarry.net.client

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

    from twisted.internet import reactor
    from quarry.auth import OfflineProfile

    factory = ExampleClientFactory(OfflineProfile("Notch"))
    factory.connect("localhost", 25565)
    reactor.run()

To log into online-mode servers, we need to talk to the Mojang session servers.
Quarry uses twisted_ under the hood, where instead of waiting for I/O to
complete, we register a callback that will be fired when login is complete::

    from twisted.internet import defer, reactor
    from quarry.mojang.profile import Profile

    @defer.inlineCallbacks
    def main():
        print("logging in...")
        profile = yield Profile.from_credentials("someone@somewhere.com", "p4ssw0rd")
        factory = ExampleClientFactory(profile)
        print("connecting...")
        factory = yield factory.connect("localhost", 25565)
        print("connected!")

    main()
    reactor.run()

API Reference
-------------

Quarry's default packet handlers call certain methods when events occur. You
might want to call ``super()`` for these methods if you reimplement them.

.. autoclass:: ClientProtocol
    :members:
    :inherited-members:
    :exclude-members: makeConnection, logPrefix

.. _twisted: https://twistedmatrix.com