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
        # x, y, z, yaw, pitch
        self.pos_look = [0, 0, 0, 0, 0]

    # Send a 'player' packet every tick
    def update_player_inc(self):
        self.pos_look[3] = (self.pos_look[3] + 5) % 360
        self.send_packet("player", self.buff_type.pack('?', True))

    # Sent a 'player position' packet every 20 ticks
    def update_player_full(self):
        self.send_packet("player_position", self.buff_type.pack('ddd?',
            self.pos_look[0],
            self.pos_look[1],
            self.pos_look[2],
            True))

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
        p_pos_look = buff.unpack('dddff')

        # 1.7.x
        if self.protocol_version <= 5:
            p_on_ground = buff.unpack('?')
            self.pos_look = p_pos_look

        # 1.8.x
        else:
            p_flags = buff.unpack('B')

            for i in range(5):
                if p_flags & (1 << i):
                    self.pos_look[i] += p_pos_look[i]
                else:
                    self.pos_look[i] = p_pos_look[i]

        # Send Player Position And Look

        # 1.7.x
        if self.protocol_version <= 5:
            self.send_packet("player_position_and_look", self.buff_type.pack(
                'ddddff?',
                self.pos_look[0],
                self.pos_look[1] - 1.62,
                self.pos_look[1],
                self.pos_look[2],
                self.pos_look[3],
                self.pos_look[4],
                True))

        # 1.8.x
        else:
            self.send_packet("player_position_and_look", self.buff_type.pack(
                'dddff?',
                self.pos_look[0],
                self.pos_look[1],
                self.pos_look[2],
                self.pos_look[3],
                self.pos_look[4],
                True))

        if not self.spawned:
            self.tasks.add_loop(1.0/20, self.update_player_inc)
            self.tasks.add_loop(1.0,    self.update_player_full)
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

    # Log in and connect
    deferred = profile.login(username, password)
    deferred.addCallbacks(
        lambda data: factory.connect(host, int(port)),
        lambda err: print("login failed:", err.value))
    factory.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])