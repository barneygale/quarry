"""
Pinger example client

Asks the server for the information normally displayed in the minecraft
multiplayer menu.
"""

from quarry.net.client import ClientFactory, ClientProtocol
from quarry.mojang.profile import Profile


class PingProtocol(ClientProtocol):
    def status_response(self, data):
        for k, v in sorted(data.items()):
            if k != "favicon":
                self.logger.info("%s --> %s" % (k, v))

        self.factory.stop()


class PingFactory(ClientFactory):
    protocol = PingProtocol


def main(args):
    # Parse options
    import optparse
    parser = optparse.OptionParser(
        usage="usage: %prog <connect-host> <connect-port>")
    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        return parser.print_usage()

    host, port = args

    # Create profile
    profile = Profile()
    profile.login_offline("quarry")

    # Create factory
    factory = PingFactory()
    factory.profile = profile

    factory.connect(host, int(port), "status")
    factory.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])