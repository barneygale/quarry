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

.. autoclass:: ClientProtocol
    :members:
    :inherited-members:
    :exclude-members: makeConnection, logPrefix

.. _twisted: https://twistedmatrix.com