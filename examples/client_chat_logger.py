"""
Chat logger example client

Stays in game and prints player chat to console.
"""

from __future__ import print_function
from quarry.net.client import ClientFactory, ClientProtocol
from quarry.mojang.profile import Profile


class ChatLoggerProtocol(ClientProtocol):
    spawned = False

    def setup(self):
        self.coords = [0, 0, 0]
        self.yaw = 0
        self.pitch = 0

    def update_player(self):
        self.yaw = (self.yaw + 5) % 360

        self.send_packet("player_look",
            self.buff_type.pack('ff?', self.yaw, self.pitch, True))

    def packet_chat_message(self, buff):
        p_text = buff.unpack_chat()

        # 1.7.x
        if self.protocol_version <= 5:
            pass
        # 1.8.x
        else:
            p_position = buff.unpack('B')

        self.logger.info(":: %s" % p_text)

    def packet_player_position_and_look(self, buff):
        p_coords = buff.unpack('ddd')
        p_yaw = buff.unpack('f')
        p_pitch = buff.unpack('f')

        # 1.7.x
        if self.protocol_version <= 5:
            p_on_ground = buff.unpack('?')

            self.coords = p_coords
            self.yaw = p_yaw
            self.pitch = p_pitch

        # 1.8.x
        else:
            p_position_flags = buff.unpack('B')

            if p_position_flags & 1 >> 0:
                self.coords[0] = 0
            if p_position_flags & 1 >> 1:
                self.coords[1] = 0
            if p_position_flags & 1 >> 2:
                self.coords[2] = 0
            if p_position_flags & 1 >> 3:
                self.pitch = 0
            if p_position_flags & 1 >> 4:
                self.yaw = 0

        self.coords = [old+new for old, new in zip(p_coords, self.coords)]
        self.yaw += p_yaw
        self.pitch += p_pitch

        # Send Player Position And Look

        # 1.7.x
        if self.protocol_version <= 5:
            self.send_packet("player_position_and_look", self.buff_type.pack(
                'ddddff?',
                self.coords[0],
                self.coords[1] - 1.62,
                self.coords[1],
                self.coords[2],
                self.yaw,
                self.pitch,
                True))

        # 1.8.x
        else:
            self.send_packet("player_position_and_look", self.buff_type.pack(
                'dddff?',
                self.coords[0],
                self.coords[1],
                self.coords[2],
                self.yaw,
                self.pitch,
                True))

        if not self.spawned:
            self.tasks.add_loop(1.0/20, self.update_player)
            self.spawned = True


class ChatLoggerFactory(ClientFactory):
    protocol = ChatLoggerProtocol


def main(args):
    # Parse options
    import optparse
    parser = optparse.OptionParser(
        usage="usage: %prog <connect-host> <connect-port> "
              "<username> <password>")
    (options, args) = parser.parse_args(args)

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
        print("login failed:", err.value)
        factory.stop()

    deferred = profile.login(username, password)
    deferred.addCallbacks(login_ok, login_failed)
    factory.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])