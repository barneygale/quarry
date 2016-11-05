"""
Example "auth" server

Ask mojang to authenticate the user
"""

from twisted.internet import reactor
from quarry.net.server import ServerFactory, ServerProtocol


class AuthProtocol(ServerProtocol):
    def player_joined(self):
        # This method gets called when a player successfully joins the server.
        #   If we're in online mode (the default), this means auth with the
        #   session server was successful and the user definitely owns the
        #   display name they claim to.

        # Call super. This switches us to "play" mode, marks the player as
        #   in-game, and does some logging.
        ServerProtocol.player_joined(self)

        # Define your own logic here. It could be an HTTP request to an API,
        #   or perhaps an update to a database table.
        display_name = self.display_name
        ip_addr = self.remote_addr.host
        self.logger.info("[%s authed with IP %s]" % (display_name, ip_addr))

        # Kick the player.
        self.close("Thanks, you are now registered!")


class AuthFactory(ServerFactory):
    protocol = AuthProtocol
    motd = "Auth Server"


def main(argv):
    # Parse options
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--host", default="", help="address to listen on")
    parser.add_argument("-p", "--port", default=25565, type=int, help="port to listen on")
    args = parser.parse_args(argv)

    # Create factory
    factory = AuthFactory()

    # Listen
    factory.listen(args.host, args.port)
    reactor.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])