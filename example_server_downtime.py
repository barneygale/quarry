from quarry.net.server import ServerFactory, ServerProtocol, register

###
### DOWNTIME SERVER
###   when a user tries to connect, the server will kick them with the MOTD
###

class DowntimeProtocol(ServerProtocol):
    @register("login", 0)
    def packet_login_start(self, buff):
        buff.discard()
        self.kick(self.factory.motd)

class DowntimeFactory(ServerFactory):
    protocol = DowntimeProtocol

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
    parser.add_option("-m", "--message",
                      dest="message", default="down for maintenance",
                      help="message to kick users with")
    (options, args) = parser.parse_args()

    # Create factory
    factory = DowntimeFactory()
    factory.motd = options.message

    # Listen
    factory.listen(options.host, options.port)
    factory.run()

if __name__ == "__main__":
    main()