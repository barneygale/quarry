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

        dimension_codec = data_packs[self.protocol_version]
        dimension_name = "minecraft:overworld"
        dimension_tag = dimension_types[self.protocol_version, dimension_name]
        world_count = 1
        world_name = "chat"

        join_game = [
            self.buff_type.pack("i?Bb", entity_id, is_hardcore, game_mode, prev_game_mode),
            self.buff_type.pack_varint(world_count),
            self.buff_type.pack_string(world_name),
            self.buff_type.pack_nbt(dimension_codec),
        ]

        if self.protocol_version >= 759:  # 1.19 needs just dimension name, <1.19 needs entire dimension nbt
            join_game.append(self.buff_type.pack_string(dimension_name))
        else:
            join_game.append(self.buff_type.pack_nbt(dimension_tag))

        join_game.append(self.buff_type.pack_string(world_name))
        join_game.append(self.buff_type.pack("q", hashed_seed))
        join_game.append(self.buff_type.pack_varint(max_players))
        join_game.append(self.buff_type.pack_varint(view_distance)),

        if self.protocol_version >= 757:  # 1.18
            join_game.append(self.buff_type.pack_varint(simulation_distance))

        join_game.append(self.buff_type.pack("????", is_reduced_debug, is_respawn_screen, is_debug, is_flat))

        if self.protocol_version >= 759:  # 1.19
            join_game.append(self.buff_type.pack("?", False))
        # Send "Join Game" packet
        self.send_packet("join_game", *join_game)


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
        self.factory.send_system("\u00a7e%s has joined." % self.display_name)

    def player_left(self):
        ServerProtocol.player_left(self)

        # Announce player left
        self.factory.send_system("\u00a7e%s has left." % self.display_name)

    def update_keep_alive(self):
        # Send a "Keep Alive" packet
        self.send_packet("keep_alive", self.buff_type.pack('Q', 0))

    def packet_chat_message(self, buff):
        # When we receive a chat message from the player, ask the factory
        # to relay it to all connected players
        self.factory.send_chat(buff, self.uuid, self.display_name, self.protocol_version >= 759)


class ChatRoomFactory(ServerFactory):
    protocol = ChatRoomProtocol
    motd = "Chat Room Server"

    def send_chat(self, packet, sender, sender_name, signed):
        message = packet.unpack_string()
        timestamp = None
        salt = None
        signature_length = 0
        signature = None
        previewed = False

        if signed:
            timestamp = packet.unpack('Q')
            salt = packet.unpack('Q')
            signature_length = packet.unpack_varint()
            signature = packet.read(signature_length)
            previewed = packet.unpack('?')

        for player in self.players:
            # 1.19+, type is now varint
            if player.protocol_version >= 759:
                # Signed, send message with signature
                if signature is not None and len(signature):
                    player.send_packet("chat_message",
                                       player.buff_type.pack_chat(message),  # Signed message
                                       player.buff_type.pack('?', False),  # No unsigned content
                                       player.buff_type.pack_varint(0),  # Message type
                                       player.buff_type.pack_uuid(sender),  # Sender UUID
                                       player.buff_type.pack_chat(sender_name),  # Sender display name
                                       player.buff_type.pack('?', False),  # No team name
                                       player.buff_type.pack('QQ', timestamp, salt),  # Timestamp, salt
                                       player.buff_type.pack_varint(signature_length),  # Signature length
                                       # Timestamp, signature length
                                       signature)  # Signature
                else:  # Not signed, send as system message to avoid client warnings
                    player.send_packet("system_message",
                                       player.buff_type.pack_chat("<%s> %s" % (sender_name, message)),
                                       player.buff_type.pack_varint(1))
            else:
                # Ignore signature as not supported by client
                player.send_packet("chat_message",
                                   player.buff_type.pack_chat("<%s> %s" % (sender_name, message)),
                                   player.buff_type.pack('B', 0),
                                   player.buff_type.pack_uuid(sender))

    def send_system(self, message):
        for player in self.players:
            # 1.19+, use system message packet
            if player.protocol_version >= 759:
                player.send_packet("system_message",
                                   player.buff_type.pack_chat(message),
                                   player.buff_type.pack_varint(1))
            else:
                player.send_packet("chat_message",
                                   player.buff_type.pack_chat(message),
                                   player.buff_type.pack('B', 0),
                                   player.buff_type.pack_uuid(UUID(int=0)))


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
