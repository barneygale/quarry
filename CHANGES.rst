Changelog
=========

master
------

- Nothing yet

v0.6.2
------

- Added support for Minecraft 1.11.2
- Added a default implementation for the "disconnect" packet, which now does
  the same thing as "login_disconnect", i.e. logs a warning and closes the
  connection.

v0.6.1
------

- Fix bundle

v0.6
----

- Added support for Minecraft 1.11
- BREAKING CHANGES!

  - Throughout the codebase, references to ``username`` have changed to
    ``display_name`` for consistency with Mojang's terminology.
  - ``Factory.run()`` and ``Factory.stop()`` have been removed for being
    misleading about the role of factories. Use twisted's ``reactor.run()``
    instead.
  - ``quarry.mojang`` has been renamed to ``quarry.auth`` and substantially
    rewritten.
  - Offline profiles are now represented by ``OfflineProfile`` objects.
  - Online profiles have a number of new static creator methods:
    - ``from_credentials()`` accepts an email address and password
    - ``from_token()`` accepts a client and access token, display name and UUID
    - ``from_file()`` loads a profile from the Mojang launcher.
  - A new ``ProfileCLI`` class provides a couple of useful methods for
    creating profiles from command-line arguments.
  - Profiles must now be provided to the ``ClientFactory`` initializer, rather
    than set as a class variable. When a profile is not given, an offline
    profile is used. In proxies, the initialiser for ``UpstreamFactory`` must
    be re-implemented if the proxy connects to the backing server in online
    mode.
  - ``Factory.auth_timeout`` has moved to ``ServerFactory.auth_timeout``.
    Clients now use ``Profile.timeout`` when calling ``/join`` endpoint.

- ``ClientFactory.connect`` returns a deferred that will fire after after
  ``reactor.connectTCP`` is called for the last time. Usually there is a small
  time delay before this happens while quarry queries the server's version.
- Clients will refresh a profile if ``/join`` indicates a token is invalid, then
  retry the ``/join`` once.
- Added a new ``SpawningClientProtocol`` class that implements enough packets
  to keep a player in-game
- Added a new ``client_messenger`` example. This bridges minecraft chat
  (in/out) with stdout and stdin.


v0.5
----

- Added ``Buffer.unpack_nbt()`` and ``Buffer.pack_nbt()`` methods for working
  with the NBT (Named Binary Tag) format.
- Added ``Buffer.unpack_position()`` method. This unpacks a 26/12/26-packed
  position.
- Added ``strip_styles`` parameter to ``Buffer.unpack_chat()``. If set to
  *false*, text is returned including old-style style escapes (U+00A7 plus a
  character)
- A stopping client factory no longer invalidates its profile.
- Added Python 3 compatibility to ``PacketDispatcher.dump_packet()``
- Fix tests for ``Buffer.unpack_chat()``

v0.4
----

- Added support for Minecraft 1.10
- Added support for Minecraft 1.9.3 and 1.9.4
- Improved the varint implementation - it now supports signed and
  magnitude-limited numbers. Also added some sensible defaults to various bits
  of quarry that use varints.
- Made ``Buffer.unpack_chat()`` not add curly braces to "translate" objects
  without accompanying "with" objects.
- Made ``Buffer.unpack_chat()`` strip old-style (\u00A7) chat escapes.

v0.3.1
------

- Added support for Minecraft 1.9.1 and 1.9.2
- Fixed protocol error in example chat logger when connecting to 1.9 servers

v0.3
----

- Added support for Minecraft 1.9
- Compression is now supported in servers
- Servers will now reject new connections when full
- Servers will now report a forced protocol version in status responses, rather
  than repeating the client's version.
- The point at which a proxy will connect to the upstream server is now
  customisable.
- Renamed "maps" packet to "map"
- Renamed "sign editor open" packet to "open sign editor"
- Renamed ``ServerFactory.favicon_path`` to ``ServerFactory.favicon``
- Renamed ``quarry.util`` to ``quarry.utils``
- Removed ``protocol_mode`` parameter from some proxy callbacks
- Added many new docstrings; made documentation use Sphinx's ``autodoc``
- Fixed exception handling when looking up a packet name. Thanks to PangeaCake
  for the fix.
- Fixed issue where an exception was raised when generating an offline-mode
  UUID in Python 3. Thanks to PangeaCake for the report.
- Fixed issue with compression in proxies when the upstream server set the
  compression threshold after passthrough had been enabled. Thanks to
  PangeaCake for the report.
- (tests) ``quarry.utils.buffer`` and ``quarry.utils.types`` are now covered.

v0.2.3
------

- (documentation) Fixed changelog for v0.2.2

v0.2.2
------

- Fixed proxies
- (documentation) Added changelog

v0.2.1
------

- (documentation) Fixed front page

v0.2
----

- Tentative Python 3 support
- Removed ``@register``. Packet handlers are now looked up by method name
- Packets are now addressed by name, rather than mode and ident
- ``Protocol.recv_addr`` renamed to ``Protocol.remote_addr``
- Client profile is automatically invalidated when ``ClientFactory`` stops
- (internals) ``PacketDispatcher`` moved from ``quarry.util`` to ``quarry.net``
- (examples) Chat logger now closely emulates vanilla client behaviour when
  sending "player"
- (documentation) It now exists!

v0.1
----

- Initial release
