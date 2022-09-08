"""
Chat logger example client

This client stays in-game after joining. It prints chat messages received from
the server and slowly rotates (thanks c45y for the idea).

This client makes no attempt to verify received signed messages.
"""

from twisted.internet import reactor, defer
from quarry.net.client import ClientFactory, SpawningClientProtocol
from quarry.net.auth import ProfileCLI


class ChatLoggerProtocol(SpawningClientProtocol):
    # 1.19+
    def packet_system_message(self, buff):
        p_text = buff.unpack_chat().to_string()
        p_display = False

        if self.protocol_version >= 760:
            p_display = not buff.unpack('?')
        else:
            p_display = buff.unpack_varint() != 2

        buff.discard()

        if p_display and p_text.strip():  # Ignore game info messages
            self.logger.info(":: %s" % p_text)

    def packet_chat_message(self, buff):
        # 1.19.1+
        if self.protocol_version >= 760:
            p_signed_message = buff.unpack_signed_message()
            buff.unpack_varint()  # Filter result
            p_position = buff.unpack_varint()
            p_sender_name = buff.unpack_chat()

            buff.discard()

            if p_position not in (1, 2):  # Ignore system and game info messages
                # Sender name is sent separately to the message text
                self.logger.info(
                    ":: <%s> %s" % (p_sender_name, p_signed_message.unsigned_content or p_signed_message.body.message))

            return

        p_text = buff.unpack_chat().to_string()

        # 1.19+
        if self.protocol_version == 759:
            p_unsigned_text = buff.unpack_optional(lambda: buff.unpack_chat().to_string())
            p_position = buff.unpack_varint()
            buff.unpack_uuid()  # Sender UUID
            p_sender_name = buff.unpack_chat()
            buff.discard()

            if p_position not in (1, 2):  # Ignore system and game info messages
                # Sender name is sent separately to the message text
                self.logger.info(":: <%s> %s" % (p_sender_name, p_unsigned_text or p_text))

        elif self.protocol_version >= 47:  # 1.8.x+
            p_position = buff.unpack('B')
            buff.discard()

            if p_position not in (1, 2) and p_text.strip():  # Ignore system and game info messages
                self.logger.info(":: %s" % p_text)

        elif p_text.strip():
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