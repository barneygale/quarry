"""
Example "auth" server

Ask mojang to authenticate the user
"""

from quarry.net.server import ServerFactory, ServerProtocol


class AuthProtocol(ServerProtocol):
    def player_joined(self):
        # This method gets called when a player successfully joins the server.
        #   If we're in online mode (the default), this means auth with the
        #   session server was successful and the user definitely owns the
        #   username they claim to.

        # Call super. This switches us to "play" mode, marks the player as
        #   in-game, and does some logging.
        ServerProtocol.player_joined(self)

        # Define your own logic here. It could be an HTTP request to an API,
        #   or perhaps an update to a database table.
        username = self.username
        ip_addr = self.recv_addr.host
        self.logger.info("[%s authed with IP %s]" % (username, ip_addr))

        # Kick the player.
        self.close("Thanks, you are now registered!")


class AuthFactory(ServerFactory):
    protocol = AuthProtocol


def main(args):
    # Parse options
    import optparse
    parser = optparse.OptionParser(
        usage="usage: %prog [options]")
    parser.add_option("-a", "--host",
                      dest="host", default="",
                      help="address to listen on")
    parser.add_option("-p", "--port",
                      dest="port", default="25565", type="int",
                      help="port to listen on")
    (options, args) = parser.parse_args(args)

    # Create factory
    factory = AuthFactory()
    factory.motd = "Auth Server"

    # Listen
    factory.listen(options.host, options.port)
    factory.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])