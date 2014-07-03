from quarry.net.client import ClientFactory, ClientProtocol, register
from quarry.mojang.profile import Profile

###
### PING CLIENT
###   gets some data about the server
###

class PingProtocol(ClientProtocol):
    protocol_mode_next = "status"

    @register("status", 0)
    def packet_status_response(self, buff):
        p_response = buff.unpack_json()
        for k, v in sorted(p_response.items()):
            if k != "favicon":
                self.logger.info("%s --> %s" % (k, v))

        self.factory.stop()


class PingFactory(ClientFactory):
    protocol = PingProtocol

def main():
    # Parse options
    import optparse
    parser = optparse.OptionParser(usage="usage: %prog host port")
    (options, args) = parser.parse_args()

    if len(args) != 2:
        return parser.print_usage()

    host, port = args

    # Create profile
    profile = Profile()
    profile.login_offline("quarry")

    # Create factory
    factory = PingFactory()
    factory.profile = profile

    factory.connect(host, int(port))
    factory.run()

if __name__ == "__main__":
    main()