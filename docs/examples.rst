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

Clients
-------

Pinger
''''''

This example client connects to a server in "status" mode to retrieve some
information about the server. The information returned is what you'd normally
see in the "Multiplayer" menu of the official client.

.. literalinclude:: ../examples/client_ping.py
    :lines: 8-

Player Lister
'''''''''''''

This client requires a Mojang account for online-mode servers. It logs in to
the server and prints the players listed in the tab menu.

.. literalinclude:: ../examples/client_player_list.py
    :lines: 7-

Chat Logger
'''''''''''

This client stays in-game after joining. It prints chat messages received from
the server and slowly rotates (thanks c45y for the idea).

.. literalinclude:: ../examples/client_chat_logger.py
    :lines: 7-

Servers
-------

Downtime Server
'''''''''''''''

This server kicks players with the MOTD when they try to connect. It can be
useful for when you want players to know that your usual server is down for
maintenance.

.. literalinclude:: ../examples/server_downtime.py
    :lines: 6-

Auth Server
'''''''''''

This server authenticates players with the mojang session server, then kicks
them. Useful for server websites that ask users for a valid Minecraft account.

.. literalinclude:: ../examples/server_auth.py
    :lines: 6-

Chat Room Server
''''''''''''''''

This server authenticates players, then spawns them in an empty world and does
the bare minimum to keep them in-game. Players can speak to eachother using
chat.