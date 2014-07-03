from quarry.net.client import ClientFactory, ClientProtocol, register
from quarry.mojang.profile import Profile

###
### PLAYER LIST CLIENT
###   logs in and prints the player list
###

class PlayerListProtocol(ClientProtocol):
    protocol_mode_next = "login"

    def setup(self):
        self.players = {}

    @register("play", 0x38)
    def packet_player_list_item(self, buff):
        p_player_name = buff.unpack_string()
        p_online = buff.unpack('?')
        p_ping = buff.unpack('h')

        if p_online:
            self.players[p_player_name] = p_ping

    @register("play", 0x08)
    def player_position_and_look(self, buff):
        buff.discard()

        for username, ping in sorted(self.players.items()):
            self.logger.info("%4sms %s" % (ping, username))

        self.factory.stop()


class PlayerListFactory(ClientFactory):
    protocol = PlayerListProtocol


def main():
    # Parse options
    import optparse
    parser = optparse.OptionParser(usage="usage: %prog host port username password")
    (options, args) = parser.parse_args()

    if len(args) != 4:
        return parser.print_usage()

    host, port, username, password = args

    # Create profile
    profile = Profile()

    # Create factory
    factory = PlayerListFactory()
    factory.profile = profile

    def login_ok(data):
        factory.connect(host, int(port))

    def login_failed(err):
        print "login failed:", err.value
        factory.stop()

    deferred = profile.login(username, password)
    deferred.addCallbacks(login_ok, login_failed)
    factory.run()

if __name__ == "__main__":
    main()