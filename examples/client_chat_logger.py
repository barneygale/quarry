"""
Chat logger example client

This client stays in-game after joining. It prints chat messages received from
the server and slowly rotates (thanks c45y for the idea).
"""

from twisted.internet import reactor, defer
from quarry.net.client import ClientFactory, SpawningClientProtocol
from quarry.net.auth import ProfileCLI


class ChatLoggerProtocol(SpawningClientProtocol):

    def packet_chat_message(self, buff):
        p_text = buff.unpack_chat()
        p_position = 0
        p_sender = None

        # 1.8.x+
        if self.protocol_version >= 47:
            p_position = buff.unpack('B')

        # 1.16.x+
        if self.protocol_version >= 736:
            p_sender = buff.unpack_uuid()

        self.logger.info(":: %s" % p_text)


class ChatLoggerFactory(ClientFactory):
    protocol = ChatLoggerProtocol


@defer.inlineCallbacks
def run(args):
    # Log in
    profile = yield ProfileCLI.make_profile(args)

    # Create factory
    factory = ChatLoggerFactory(profile)

    # Connect!
    factory.connect(args.host, args.port)


def main(argv):
    parser = ProfileCLI.make_parser()
    parser.add_argument("host")
    parser.add_argument("-p", "--port", default=25565, type=int)
    args = parser.parse_args(argv)

    run(args)
    reactor.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
