from quarry.net.server import ServerFactory, ServerProtocol

###
### AUTH SERVER
###   ask mojang to authenticate the user
###

class AuthProtocol(ServerProtocol):
    def player_joined(self):
        self.logger.info("%s auth OK" % self.username)
        self.kick("Thanks")

    def auth_failed(self, err):
        ServerProtocol.auth_failed(self, err)
        self.logger.info("%s auth failed: %s" % (self.username, err.value))

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