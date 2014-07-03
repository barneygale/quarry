from quarry.net.server import ServerFactory, ServerProtocol

###
### AUTH SERVER
###   ask mojang to authenticate the user
###

class AuthProtocol(ServerProtocol):
    def player_joined(self):
        self.logger.info("Auth OK: %s" % self.username)

        # Some logic here

        self.close("Thanks, you are now registered!")


class AuthFactory(ServerFactory):
    protocol = AuthProtocol


def main():
    # Parse options
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-a", "--host",
                      dest="host", default="",
                      help="address to listen on")
    parser.add_option("-p", "--port",
                      dest="port", default="25565", type="int",
                      help="port to listen on")
    (options, args) = parser.parse_args()

    # Create factory
    factory = AuthFactory()
    factory.motd = "Auth Server"

    # Listen
    factory.listen(options.host, options.port)
    factory.run()

if __name__ == "__main__":
    main()