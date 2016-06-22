Changelog
=========

master
------

- Nothing yet

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
