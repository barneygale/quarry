"""
Example "chat room" server

This server authenticates players, then spawns them in an empty world and does
the bare minimum to keep them in-game. Players can speak to eachother using
chat.

Supports Minecraft 1.15 & 1.16. Earlier versions will not work as the packet formats
differ.
"""

from twisted.internet import reactor
from quarry.net.server import ServerFactory, ServerProtocol
from quarry.types.nbt import TagByte, TagCompound, TagFloat, TagInt, TagList, TagLong, TagRoot, TagString
from quarry.types.uuid import UUID


class ChatRoomProtocol(ServerProtocol):
    def player_joined(self):
        # Call super. This switches us to "play" mode, marks the player as
        #   in-game, and does some logging.
        ServerProtocol.player_joined(self)
        
        dim_name = "minecraft:the_end"

        if self.protocol_version > 736: # Minecraft 1.16.2
            # Send "Join Game" packet
            biome_codec = TagCompound({
                "type" : TagString("minecraft:worldgen/biome"),
                "value": TagList([
                    TagCompound({
                        'name'   : TagString("minecraft:plains"), # Client crashes if you do not define plains
                        'id'     : TagInt(1),
                        'element': TagCompound({
                            'precipitation': TagString("none"),
                            'effects'      : TagCompound({
                                'sky_color'      : TagInt(0),
                                'water_fog_color': TagInt(0),
                                'fog_color'      : TagInt(0),
                                'water_color'    : TagInt(0),
                            }),
                            'depth'      : TagFloat(0.1),
                            'temperature': TagFloat(0.5),
                            'scale'      : TagFloat(0.2),
                            'downfall'   : TagFloat(0.5),
                            'category'   : TagString("plains")
                        }),
                    })
                ])
            })
            dim_settings = TagCompound({
                "natural"             : TagByte(1),
                "ambient_light"       : TagFloat(0.0),
                "has_ceiling"         : TagByte(0),
                "has_skylight"        : TagByte(0),
                "fixed_time"          : TagLong(6000),
                "ultrawarm"           : TagByte(0),
                "has_raids"           : TagByte(0),
                "respawn_anchor_works": TagByte(0),
                "bed_works"           : TagByte(0),
                "piglin_safe"         : TagByte(0),
                "logical_height"      : TagInt(256),
                "infiniburn"          : TagString("minecraft:infiniburn_end"),
                "coordinate_scale"    : TagFloat(1.0)
            })
            dim_codec = TagRoot({
                '': TagCompound({
                    "minecraft:dimension_type": TagCompound({
                        "type" : TagString("minecraft:dimension_type"),
                        "value": TagList([
                            TagCompound({
                                "name"   : TagString(dim_name),
                                "id"     : TagInt(0),
                                "element": dim_settings
                            }),
                        ]),
                    }),
                    "minecraft:worldgen/biome": biome_codec
                })
            })
            current_dim = TagRoot({
                '': dim_settings,
            })

            self.send_packet("join_game",
                             self.buff_type.pack("i?BB", 0, False, 3, 3),           # entity id, hardcore, game mode, previous game mode
                             self.buff_type.pack_varint(1),                         # world count
                             self.buff_type.pack_string(dim_name),                  # world name(s)
                             self.buff_type.pack_nbt(dim_codec),                    # dimension registry
                             self.buff_type.pack_nbt(current_dim),                  # current dimension
                             self.buff_type.pack_string(dim_name),                  # world name
                             self.buff_type.pack("q", 42),                          # hashed seed
                             self.buff_type.pack_varint(0),                         # max players (unused)
                             self.buff_type.pack_varint(2),                         # view distance
                             self.buff_type.pack("????", True, True, False, True))  # respawn screen, debug world, flat world

        elif self.protocol_version > 578:  # Minecraft 1.16.1
            # Send "Join Game" packet
            dim_codec = TagRoot({
                '': TagCompound({
                    "dimension": TagList([
                        TagCompound({
                            "name"                : TagString(dim_name),
                            "natural"             : TagByte(0),
                            "ambient_light"       : TagFloat(0.0),
                            "has_ceiling"         : TagByte(0),
                            "has_skylight"        : TagByte(0),
                            "fixed_time"          : TagLong(6000),
                            "shrunk"              : TagByte(0),
                            "ultrawarm"           : TagByte(0),
                            "has_raids"           : TagByte(1),
                            "respawn_anchor_works": TagByte(0),
                            "bed_works"           : TagByte(0),
                            "piglin_safe"         : TagByte(0),
                            "logical_height"      : TagInt(256),
                            "infiniburn"          : TagString("minecraft:infiniburn_end"),
                        }),
                    ])
                })
            })
            self.send_packet("join_game",
                             self.buff_type.pack("iBB", 0, 3, 3),                   # entity id, game mode, previous game mode
                             self.buff_type.pack_varint(1),                         # world count
                             self.buff_type.pack_string(dim_name),                  # world name(s)
                             self.buff_type.pack_nbt(dim_codec),                    # dimension registry
                             self.buff_type.pack_string(dim_name),                  # dimension
                             self.buff_type.pack_string(dim_name),                  # world name
                             self.buff_type.pack("qB", 42, 0),                      # hashed seed, max players (unused)
                             self.buff_type.pack_varint(2),                         # view distance
                             self.buff_type.pack("????", True, True, False, True))  # respawn screen, debug world, flat world
        else:  # Minecraft 1.15
            # Send "Join Game" packet
            self.send_packet("join_game",
                self.buff_type.pack("iBiqB",
                    0,                              # entity id
                    3,                              # game mode
                    0,                              # dimension
                    0,                              # hashed seed
                    0),                             # max players
                self.buff_type.pack_string("flat"), # level type
                self.buff_type.pack_varint(1),      # view distance
                self.buff_type.pack("??",
                    False,                          # reduced debug info
                    True))                          # show respawn screen

        # Send "Player Position and Look" packet
        self.send_packet("player_position_and_look",
            self.buff_type.pack("dddff?",
                0,                         # x
                255,                       # y
                0,                         # z
                0,                         # yaw
                0,                         # pitch
                0b00000),                  # flags
            self.buff_type.pack_varint(0)) # teleport id

        # Start sending "Keep Alive" packets
        self.ticker.add_loop(20, self.update_keep_alive)

        # Announce player joined
        self.factory.send_chat(u"\u00a7e%s has joined." % self.display_name)

    def player_left(self):
        ServerProtocol.player_left(self)

        # Announce player left
        self.factory.send_chat(u"\u00a7e%s has left." % self.display_name)

    def update_keep_alive(self):
        # Send a "Keep Alive" packet

        # 1.7.x
        if self.protocol_version <= 338:
            payload =  self.buff_type.pack_varint(0)

        # 1.12.2
        else:
            payload = self.buff_type.pack('Q', 0)

        self.send_packet("keep_alive", payload)

    def packet_chat_message(self, buff):
        # When we receive a chat message from the player, ask the factory
        # to relay it to all connected players
        p_text = buff.unpack_string()
        self.factory.send_chat("<%s> %s" % (self.display_name, p_text), sender=self.uuid)


class ChatRoomFactory(ServerFactory):
    protocol = ChatRoomProtocol
    motd = "Chat Room Server"

    def send_chat(self, message, sender=UUID(int=0)):
        for player in self.players:
            data = player.buff_type.pack_chat(message) + player.buff_type.pack('B', 0)
            if player.protocol_version > 578:
                data += player.buff_type.pack_uuid(sender)
            player.send_packet("chat_message", data)


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
