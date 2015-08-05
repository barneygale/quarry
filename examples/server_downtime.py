"""
Example "downtime" server

When a user tries to connect, the server will kick them with the MOTD
"""

from quarry.net.server import ServerFactory, ServerProtocol


class DowntimeProtocol(ServerProtocol):
    def packet_login_start(self, buff):
        buff.discard()
        self.close(self.factory.motd)


class DowntimeFactory(ServerFactory):
    protocol = DowntimeProtocol


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
    parser.add_option("-m", "--message",
                      dest="message", default="We're down for maintenance",
                      help="message to kick users with")
    (options, args) = parser.parse_args(args)

    # Create factory
    factory = DowntimeFactory()
    factory.motd = options.message

    # Listen
    factory.listen(options.host, options.port)
    factory.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])