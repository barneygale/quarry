from quarry.net.proxy import ProxyServerFactory, Bridge, register

###
### PROXY SERVER
###   Allows a client to turn on "quiet mode" which hides chat messages
###


class ExampleProxyBridge(Bridge):
    quiet_mode = False

    @register("play", 0x01, "downstream")
    def packet_client_chat(self, buff):
        buff.save()
        chat_message = buff.unpack_string()
        self.logger.info(" >> %s" % chat_message)


        if chat_message.startswith("/quiet"):
            # Switch mode
            self.quiet_mode = not self.quiet_mode

            msg = "Quiet mode %s" % \
                  (self.quiet_mode and "enabled" or "disabled")
            self.downstream.send_packet(0x02, self.buff_type.pack_chat(msg))

        elif self.quiet_mode and not chat_message.startswith("/"):
            # Don't let the player send chat messages in quiet mode
            msg = "Can't send messages while in quiet mode"
            self.downstream.send_packet(0x02, self.buff_type.pack_chat(msg))

        else:
            # Pass to upstream
            buff.restore()
            self.upstream.send_packet(0x01,
                buff.unpack_all())

    @register("play", 0x02, "upstream")
    def packet_server_chat(self, buff):
        buff.save()
        chat_message = buff.unpack_chat()
        self.logger.info(" :: %s" % chat_message)

        if self.quiet_mode and  chat_message.startswith("<"):
            # Ignore message we're in quiet mode and it looks like chat
            pass

        else:
            # Pass to downstream
            buff.restore()
            self.downstream.send_packet(0x02, buff.unpack_all())


class ExampleProxyServerFactory(ProxyServerFactory):
    bridge_class = ExampleProxyBridge
    motd = "Proxy Server"


def main():
    # Parse options
    import optparse
    parser = optparse.OptionParser("usage: %prog [options] connect-host connect-port")
    parser.add_option("-a", "--listen-host",
                      dest="listen_host", default="",
                      help="address to listen on")
    parser.add_option("-p", "--listen-port",
                      dest="listen_port", default="25565", type="int",
                      help="port to listen on")
    (options, args) = parser.parse_args()

    if len(args) != 2:
        return parser.print_usage()

    # Create factory
    factory = ExampleProxyServerFactory()
    factory.motd = "Proxy Server"
    factory.connect_host = args[0]
    factory.connect_port = int(args[1])

    # Listen
    factory.listen(options.listen_host, options.listen_port)
    factory.run()

if __name__ == "__main__":
    main()