Changelog
=========

master
------

- Renamed ``quarry.util`` to `quarry.utils``
- Removed ``protocol_mode`` parameter from some proxy callbacks

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