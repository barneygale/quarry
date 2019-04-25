"""
"Quiet mode" example proxy

Allows a client to turn on "quiet mode" which hides chat messages
"""

from twisted.internet import reactor
from quarry.net.proxy import DownstreamFactory, Bridge


class QuietBridge(Bridge):
    quiet_mode = False

    def packet_upstream_chat_message(self, buff):
        buff.save()
        chat_message = self.read_chat(buff, "upstream")
        self.logger.info(" >> %s" % chat_message)

        if chat_message.startswith("/quiet"):
            # Switch mode
            self.quiet_mode = not self.quiet_mode

            action = self.quiet_mode and "enabled" or "disabled"
            msg = "Quiet mode %s" % action
            self.downstream.send_packet("chat_message",
                                        self.write_chat(msg, "downstream"))

        elif self.quiet_mode and not chat_message.startswith("/"):
            # Don't let the player send chat messages in quiet mode
            msg = "Can't send messages while in quiet mode"
            self.downstream.send_packet("chat_message",
                                        self.write_chat(msg, "downstream"))

        else:
            # Pass to upstream
            buff.restore()
            self.upstream.send_packet("chat_message", buff.read())

    def packet_downstream_chat_message(self, buff):
        chat_message = self.read_chat(buff, "downstream")
        self.logger.info(" :: %s" % chat_message)

        if self.quiet_mode and chat_message.startswith("<"):
            # Ignore message we're in quiet mode and it looks like chat
            pass

        else:
            # Pass to downstream
            buff.restore()
            self.downstream.send_packet("chat_message", buff.read())

    def read_chat(self, buff, direction):
        buff.save()
        if direction == "upstream":
            p_text = buff.unpack_string()
            return p_text
        elif direction == "downstream":
            p_text = str(buff.unpack_chat())

            # 1.7.x
            if self.upstream.protocol_version <= 5:
                p_position = 0

            # 1.8.x
            else:
                p_position = buff.unpack('B')

            if p_position in (0, 1):
                return p_text

    def write_chat(self, text, direction):
        if direction == "upstream":
            return self.buff_type.pack_string(text)
        elif direction == "downstream":
            data = self.buff_type.pack_chat(text)

            # 1.7.x
            if self.downstream.protocol_version <= 5:
                pass

            # 1.8.x
            else:
                data += self.buff_type.pack('B', 0)

            return data


class QuietDownstreamFactory(DownstreamFactory):
    bridge_class = QuietBridge
    motd = "Proxy Server"


def main(argv):
    # Parse options
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--listen-host", default="", help="address to listen on")
    parser.add_argument("-p", "--listen-port", default=25565, type=int, help="port to listen on")
    parser.add_argument("-b", "--connect-host", default="127.0.0.1", help="address to connect to")
    parser.add_argument("-q", "--connect-port", default=25565, type=int, help="port to connect to")
    args = parser.parse_args(argv)

    # Create factory
    factory = QuietDownstreamFactory()
    factory.connect_host = args.connect_host
    factory.connect_port = args.connect_port

    # Listen
    factory.listen(args.listen_host, args.listen_port)
    reactor.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])