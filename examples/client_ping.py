"""
Pinger example client

This example client connects to a server in "status" mode to retrieve some
information about the server. The information returned is what you'd normally
see in the "Multiplayer" menu of the official client.
"""

from twisted.internet import reactor
from quarry.net.client import ClientFactory, ClientProtocol


class PingProtocol(ClientProtocol):

    def status_response(self, data):
        for k, v in sorted(data.items()):
            if k != "favicon":
                self.logger.info("%s --> %s" % (k, v))

        reactor.stop()


class PingFactory(ClientFactory):
    protocol = PingProtocol
    protocol_mode_next = "status"


def main(argv):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("-p", "--port", default=25565, type=int)
    args = parser.parse_args(argv)

    factory = PingFactory()
    factory.connect(args.host, args.port)
    reactor.run()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])