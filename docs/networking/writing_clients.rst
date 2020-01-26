Writing a Client
================


.. currentmodule:: quarry.net.client

A client is generally made up of three parts:

- A :class:`~quarry.net.auth.Profile` or
  :class:`~quarry.net.auth.OfflineProfile` object, representing the Minecraft
  account to use.
- A subclass of :class:`ClientFactory`. Client factories don't do a lot;
  simply pass a profile to its initializer and then call
  :meth:`~ClientFactory.connect`. You may also want to subclass from twisted's
  ReconnectingClientFactory_
- A subclass of :class:`ClientProtocol`. This represents your connection to the
  server.

.. seealso::
    :doc:`factories_protocols`


Skeleton Client
---------------


By default quarry proceeds through the authentication process and then switches
into the "play" protocol mode. The skeleton client below will receive world
data from the server, but as it does not send any position updates it will be
disconnected by the server after a few seconds. Please see the :doc:`/examples`
for less silly clients.

.. code-block:: python

    from twisted.internet import defer, reactor
    from quarry.net.client import ClientFactory, ClientProtocol
    from quarry.auth import Profile


    class ExampleClientProtocol(ClientProtocol):
        pass


    class ExampleClientFactory(ClientFactory):
        protocol = ExampleClientProtocol


    @defer.inlineCallbacks
    def main():
        print("logging in...")
        profile = yield Profile.from_credentials(
            "someone@somewhere.com", "p4ssw0rd")
        factory = ExampleClientFactory(profile)
        print("connecting...")
        factory = yield factory.connect("localhost", 25565)
        print("connected!")


    if __name__ == "__main__":
        main()
        reactor.run()



Offline Profiles
----------------

.. module:: quarry.net.auth

Use an :class:`OfflineProfile` if you only need to log into offline-mode
servers::

    from quarry.net.auth import OfflineProfile
    profile = OfflineProfile("Notch")

.. class:: OfflineProfile

    .. automethod:: __init__

    .. automethod:: from_display_name

        For compatibility with the ``from_`` methods on :class:`Profile`, this
        method returns a ``Deferred`` that immediately fires with a constructed
        :class:`OfflineProfile` object.

Online Profiles
---------------

Quarry also provides a number of methods for logging in to the Mojang session
servers. Each of these returns a Deferred_ that will fire with a
:class:`Profile` object when login succeeds. Defining a callback and then
calling ``Profile.from_credentials(...).addCallback(myfunc)`` is one approach,
but it's usually cleaner to use inlineCallbacks_, as in the first example.


.. autoclass:: Profile
    :undoc-members:
    :members: from_credentials, from_token, from_file, to_file


.. _ReconnectingClientFactory: http://twistedmatrix.com/documents/current/api/twisted.internet.protocol.ReconnectingClientFactory.html
.. _Deferred: http://twistedmatrix.com/documents/current/api/twisted.internet.defer.Deferred.html
.. _inlineCallbacks: http://twistedmatrix.com/documents/current/api/twisted.internet.defer.inlineCallbacks.html
