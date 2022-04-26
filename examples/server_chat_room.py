"""
Example "chat room" server

This server authenticates players, then spawns them in an empty world and does
the bare minimum to keep them in-game. Players can speak to each other using
chat.

Supports Minecraft 1.16.3+.
"""

from twisted.internet import reactor
from quarry.net.server import ServerFactory, ServerProtocol
from quarry.types.uuid import UUID
from quarry.data.data_packs import data_packs, dimension_types


class ChatRoomProtocol(ServerProtocol):
    def player_joined(self):
        # Call super. This switches us to "play" mode, marks the player as
        #   in-game, and does some logging.
        ServerProtocol.player_joined(self)

        # Build up fields for "Join Game" packet
        entity_id = 0
        max_players = 0
        hashed_seed = 42
        view_distance = 2
        simulation_distance = 2
        game_mode = 3
        prev_game_mode = 3
        is_hardcore = False
        is_respawn_screen = True
        is_reduced_debug = False
        is_debug = False
        is_flat = False
        dimension_count = 1
        dimension_name = "chat"
        dimension_type = dimension_types[self.protocol_version, "minecraft:overworld"]
        data_pack = data_packs[self.protocol_version]

        join_game = [
            self.buff_type.pack("i?BB", entity_id, is_hardcore, game_mode, prev_game_mode),
            self.buff_type.pack_varint(dimension_count),
            self.buff_type.pack_string(dimension_name),
            self.buff_type.pack_nbt(data_pack),
            self.buff_type.pack_nbt(dimension_type),
            self.buff_type.pack_string(dimension_name),
            self.buff_type.pack("q", hashed_seed),
            self.buff_type.pack_varint(max_players),
            self.buff_type.pack_varint(view_distance),
        ]

        if self.protocol_version >= 757:  # 1.18
            join_game.append(self.buff_type.pack_varint(simulation_distance))

        # Send "Join Game" packet
        self.send_packet(
            "join_game",
            *join_game,
            self.buff_type.pack("????", is_reduced_debug, is_respawn_screen, is_debug, is_flat))

        # Send "Player Position and Look" packet
        self.send_packet(
            "player_position_and_look",
            self.buff_type.pack("dddff?",
                0,                         # x
                500,                       # y  Must be >= build height to pass the "Loading Terrain" screen on 1.18.2
                0,                         # z
                0,                         # yaw
                0,                         # pitch
                0b00000),                  # flags
            self.buff_type.pack_varint(0), # teleport id
            self.buff_type.pack("?", True)) # Leave vehicle,
        # Start sending "Keep Alive" packets
        self.ticker.add_loop(20, self.update_keep_alive)

        # Announce player joined
        self.factory.send_chat("\u00a7e%s has joined." % self.display_name)

    def player_left(self):
        ServerProtocol.player_left(self)

        # Announce player left
        self.factory.send_chat("\u00a7e%s has left." % self.display_name)

    def update_keep_alive(self):
        # Send a "Keep Alive" packet
        self.send_packet("keep_alive", self.buff_type.pack('Q', 0))

    def packet_chat_message(self, buff):
        # When we receive a chat message from the player, ask the factory
        # to relay it to all connected players
        p_text = buff.unpack_string()
        self.factory.send_chat("<%s> %s" % (self.display_name, p_text),
                               sender=self.uuid)


class ChatRoomFactory(ServerFactory):
    protocol = ChatRoomProtocol
    motd = "Chat Room Server"

    def send_chat(self, message, sender=None):
        if sender is None:
            sender = UUID(int=0)

        for player in self.players:
            player.send_packet(
                "chat_message",
                player.buff_type.pack_chat(message),
                player.buff_type.pack('b', 0),
                player.buff_type.pack_uuid(sender))


def main(argv):
    # Parse options
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--host", default="", help="address to listen on")
    parser.add_argument("-p", "--port", default=25565, type=int, help="port to listen on")
    parser.add_argument("--offline", action="store_true", help="offline server")
    args = parser.parse_args(argv)

    # Create factory
    factory = ChatRoomFactory()

    factory.online_mode = not args.offline

    # Listen
    factory.listen(args.host, args.port)
    reactor.run()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
