# Quarry

Minecraft protocol implementation - write your own bots, relays, proxies, etc.

Quarry does not implement every packet, only enough to get through the login
sequence. Users will need to pack and unpack packets they're interested in, but
most of the hard stuff (login, session, encryption) is taken care of for you.

Consult http://wiki.vg/Protocol for packet structs

## examples

The distribution includes a few example uses of the `quarry` module.

### clients

* Pinger: does a "server list ping" to get motd, player count, etc
* Player lister: joins the game, prints the player list to console, quits the
  game
* Chat logger: joins the game, prints in-game chat to console, slowly rotates

### servers

* Downtime server: kicks players with the MOTD when they try to connect
* Auth server: authenticate users with the mojang session server, then kick
  them

## requirements

* python 2.7
* pycrypto
* twisted
