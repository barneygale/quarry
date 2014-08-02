from twisted.internet import task

from quarry.net.client import ClientFactory, ClientProtocol, register
from quarry.mojang.profile import Profile

###
### CHAT LOGGER CLIENT
###   stays in game and prints player chat to console
###

class ChatLoggerProtocol(ClientProtocol):
    protocol_mode_next = "login"

    coords = (0, 0, 0)
    yaw = 0
    pitch = 0
    on_ground = 0

    loop = None

    def update_player(self):
        self.yaw = (self.yaw + 5) % 360

        self.send_packet(0x05, self.buff_type.pack('ff?',
            self.yaw,
            self.pitch,
            self.on_ground))

    @register("play", 0x02)
    def packet_chat_message(self, buff):
        p_data = buff.unpack_json()
        self.logger.info(p_data)

    @register("play", 0x08)
    def packet_player_position_and_look(self, buff):
        self.coords = buff.unpack('ddd')
        self.yaw = buff.unpack('f')
        self.pitch = buff.unpack('f')
        self.on_ground = buff.unpack('?')

        # Send Player Position And Look
        self.send_packet(0x06, self.buff_type.pack('ddddff?',
            self.coords[0],
            self.coords[1] - 1.62,
            self.coords[1],
            self.coords[2],
            self.yaw,
            self.pitch,
            self.on_ground))

        if not self.loop:
            self.loop = task.LoopingCall(self.update_player)
            self.loop.start(1.0/20, now=False)


class ChatLoggerFactory(ClientFactory):
    protocol = ChatLoggerProtocol


def main():
    # Parse options
    import optparse
    parser = optparse.OptionParser(
        usage="usage: %prog host port username password")
    (options, args) = parser.parse_args()

    if len(args) != 4:
        return parser.print_usage()

    host, port, username, password = args

    # Create profile
    profile = Profile()

    # Create factory
    factory = ChatLoggerFactory()
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