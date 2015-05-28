************************************
Quarry: a Minecraft protocol library
************************************

Write your own bots, servers, proxies, etc!

- Quarry fully implements the design of the minecraft protocol - packet
  structure, modes, compression, etc.
- Quarry implements only a handful of packet types; enough to get you through
  the login sequence both client- and server-side. This includes talking to
  the Mojang session servers and setting up encryption.
- Any `other packets`_ you're interested in you'll need to implement yourself.
  Quarry gives you support for some Minecraft data types and reasonably robust
  error checking.

========
Examples
========

The distribution includes a few example uses of the ``quarry`` module. From
the root of this repository, you can:

.. code-block:: bash

    # List examples
    $ python -m examples

    # Run an example
    $ python -m examples.blah

If you have ``quarry`` in your python search path, you can run the example
files directly.

-------
Clients
-------

- **Pinger**: Connects to a server and retrieves the MOTD, player count, etc
- **Player lister**: Joins a server and prints the player list to console.
- **Chat logger**: Joins a server and prints in-game chat to console while
  rotating creepily (thanks c45y for the idea)

-------
Servers
-------

- **Downtime server**: Kicks players with the MOTD when they try to connect.
  Useful for when you want players to know that your usual server is down for
  maintenance etc.
- **Auth server**: Authenticate players with the mojang session server, then
  kicks them. Sseful for server websites that ask users for a valid Minecraft
  account.

-------
Proxies
-------

- **Quiet proxy**: Lets users turn on "quiet" mode that hides chat from the
  server

============
Requirements
============

- python 2.7
- pyca/cryptography >= 0.9
- twisted

.. _other packets: http://wiki.vg/Protocol