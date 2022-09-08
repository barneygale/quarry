"""
Example "chat room" server which supports chat signing

Clients on versions which use the same method of chat signing will receive signed messages from each other.
Clients which use a different method of signing will receive system messages.
Clients that don't support signing will receive regular chat messages.

This example also implements the player list, which is used for sending the player public keys required for verifying
signed chat.

Signed chat messages are verified in a similar way to the vanilla server. Messages with an invalid signature, with a
timestamp older than the previous message, or with an invalid last seen list will not be accepted.
If the server is started in offline mode, it will not attempt to verify signed messages.

Supports Minecraft 1.16.3+.
"""
from typing import List

from twisted.internet import reactor
from quarry.net.server import ServerFactory, ServerProtocol
from quarry.types.chat import SignedMessage, SignedMessageHeader, SignedMessageBody, Message, LastSeenMessage
from quarry.types.uuid import UUID
from quarry.data.data_packs import data_packs, dimension_types


class ChatRoomProtocol(ServerProtocol):
    previous_timestamp = 0  # Timestamp of last chat message sent by the client, used for out-of-order chat checking
    previous_signature = None  # Signature of the last chat message sent by the client, used as part of the next message's signature
    pending_messages = []  # Chat messages pending acknowledgement by the client
    previously_seen = []  # Chat messages acknowledged by the client in the last chat message

    def player_joined(self):
        # Call super. This switches us to "play" mode, marks the player as
        #   in-game, and does some logging.
        ServerProtocol.player_joined(self)

        # Send server data packet on 1.19+
        if self.protocol_version >= 760:
            self.send_packet('server_data',
                             self.buff_type.pack('????',
                                                 False,                      # Optional description
                                                 False,                      # Optional favicon
                                                 False,                      # Disable chat previews
                                                 self.factory.online_mode))  # Enforce chat signing when in online mode
        elif self.protocol_version == 759:  # 1.19 lacks enforce chat signing field
            self.send_packet('server_data', self.buff_type.pack('???', False, False, False))

        # Send join game packet
        self.factory.send_join_game(self)

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
            self.buff_type.pack_varint(0),  # teleport id
            self.buff_type.pack("?", True))  # Leave vehicle,

        # Start sending "Keep Alive" packets
        self.ticker.add_loop(20, self.update_keep_alive)

        # Announce player join to other players
        self.factory.broadcast_player_join(self)

        # Send full player list
        self.factory.send_player_list_add(self, self.factory.players)

    def player_left(self):
        ServerProtocol.player_left(self)

        # Announce player leave to other players
        self.factory.broadcast_player_leave(self)

    def update_keep_alive(self):
        # Send a "Keep Alive" packet
        self.send_packet("keep_alive", self.buff_type.pack('Q', 0))

    def packet_chat_message(self, buff):
        if self.protocol_mode != 'play':
            return

        message = buff.unpack_string()

        # 1.19+, messages may be signed
        if self.protocol_version >= 759:
            timestamp = buff.unpack('Q')
            salt = buff.unpack('Q')
            signature = buff.unpack_byte_array()
            signature_version = 760 if self.protocol_version >= 760 else 759  # 1.19.1 signature format is different
            buff.unpack('?')  # Whether preview was accepted, not implemented here
            last_seen = []
            last_received = None

            # Ignore signature if player has no key (i.e offline mode)
            if self.public_key_data is None:
                signature = None
            else:
                # 1.19.1+ includes list of "last seen" messages
                if self.protocol_version >= 760:
                    last_seen = buff.unpack_last_seen_list()  # List of previously sent messages acknowledged by the client
                    last_received = buff.unpack_optional(buff.pack_last_seen_entry)  # Optional "last received" message

            header = SignedMessageHeader(self.uuid, self.previous_signature)
            body = SignedMessageBody(message, timestamp, salt, None, last_seen)
            signed_message = SignedMessage(header, signature, signature_version, body)

            # Validate the message
            if self.validate_signed_message(signed_message, last_received) is False:
                buff.discard()
                return

            # Update previous message data from current message
            self.previous_timestamp = signed_message.body.timestamp
            self.previous_signature = signed_message.signature
            self.previously_seen = signed_message.body.last_seen

            self.factory.broadcast_signed_chat(signed_message, self.display_name)
        else:
            self.factory.broadcast_unsigned_chat(message, self.uuid, self.display_name)

        buff.discard()

    def validate_signed_message(self, message: SignedMessage, last_received: LastSeenMessage = None):
        # Kick player if this message is older than the previous one
        if message.body.timestamp < self.previous_timestamp:
            self.logger.warning("{} sent out-of-order chat: {}".format(self.display_name, message.body.message))
            self.close(Message({'translate': 'multiplayer.disconnect.out_of_order_chat'}))
            return False

        if self.validate_last_seen(message.body.last_seen, last_received) is False:
            return False

        # Kick player if we cannot verify the message signature
        if self.public_key_data is not None and message.verify(self.public_key_data.key) is False:
            self.close(Message({'translate': 'multiplayer.disconnect.unsigned_chat'}))
            return False

    # Validate the last seen list (and optional last received message)
    # The last seen list is a list of the latest messages sent by other players, one per player
    def validate_last_seen(self, last_seen: List[LastSeenMessage], last_received: LastSeenMessage = None):
        errors = []
        profiles = []

        # The last seen list should never be shorter than the previous one
        if len(last_seen) < len(self.previously_seen):
            errors.append('Previously present messages removed from context')

        # Get indices of last seen messages to validate ordering
        indices = self.calculate_indices(last_seen, last_received)
        previous_index = -sys.maxsize - 1

        # Loop over indices to see if the message order is correct
        for index in indices:
            if index == -sys.maxsize - 1:  # Message wasn't in previously_seen or pending_messages lists
                errors.append('Unknown message')
            elif index < previous_index:  # Message is earlier than previous message
                errors.append('Messages received out of order')
            else:
                previous_index = index

        # Remove seen messages (and any older ones from the same players) from the pending list
        if previous_index >= 0:
            self.pending_messages = self.pending_messages[previous_index + 1::]

        # All last seen entries should be from different players
        for entry in last_seen:
            if entry.sender in profiles:
                errors.append('Multiple entries for single profile')
                break

            profiles.append(entry.sender)

        # Kick player if any validation fails
        if len(errors):
            self.logger.warning("Failed to validate message from {}, reasons: {}"
                                .format(self.display_name, ', '.join(errors)))
            self.close(Message({'translate': 'multiplayer.disconnect.chat_validation_failed'}))
            return False

        return True

    # Returns an array containing the positions of each of the given last_seen messages
    # (and the optional last_received message) in the previously_seen and pending_messages lists
    # A valid last_seen list should contain messages ordered oldest to newest, meaning the resulting array should
    # contain indices in ascending order
    def calculate_indices(self, last_seen: List[LastSeenMessage], last_received: LastSeenMessage = None):
        indices = [-sys.maxsize - 1] * len(last_seen)  # Populate starting lists with min value, indicating a message wasn't found

        # Get indices of any last seen messages which are in the previously seen list
        for index, value in enumerate(self.previously_seen):
            try:
                position = last_seen.index(value)
                indices[position] = -index - 1  # Negate previously seen entries to order them "before" pending entries
            except ValueError:  # Not in list
                continue

        # Get indices of any last seen messages which are in the pending messages list
        for index, value in enumerate(self.pending_messages):
            try:
                position = last_seen.index(value)
                indices[position] = index
            except ValueError:  # Not in list
                continue

        # List will be in descending order here, reverse it
        indices.reverse()

        # Get index of last received message if present
        if last_received is not None:
            try:
                indices.append(self.pending_messages.index(last_received))
            except ValueError:
                indices.append(-sys.maxsize - 1)
                pass

        return indices


class ChatRoomFactory(ServerFactory):
    protocol = ChatRoomProtocol
    motd = "Chat Room Server"

    def send_join_game(self, player):
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

        dimension_codec = data_packs[player.protocol_version]
        dimension_name = "minecraft:overworld"
        dimension_tag = dimension_types[player.protocol_version, dimension_name]
        world_count = 1
        world_name = "chat"

        join_game = [
            player.buff_type.pack("i?Bb", entity_id, is_hardcore, game_mode, prev_game_mode),
            player.buff_type.pack_varint(world_count),
            player.buff_type.pack_string(world_name),
            player.buff_type.pack_nbt(dimension_codec),
        ]

        if player.protocol_version >= 759:  # 1.19+ needs just dimension name, <1.19 needs entire dimension nbt
            join_game.append(player.buff_type.pack_string(dimension_name))
        else:
            join_game.append(player.buff_type.pack_nbt(dimension_tag))

        join_game.append(player.buff_type.pack_string(world_name))
        join_game.append(player.buff_type.pack("q", hashed_seed))
        join_game.append(player.buff_type.pack_varint(max_players))
        join_game.append(player.buff_type.pack_varint(view_distance)),

        if player.protocol_version >= 757:  # 1.18
            join_game.append(player.buff_type.pack_varint(simulation_distance))

        join_game.append(player.buff_type.pack("????", is_reduced_debug, is_respawn_screen, is_debug, is_flat))

        if player.protocol_version >= 759:  # 1.19
            join_game.append(player.buff_type.pack("?", False))

        # Send "Join Game" packet
        player.send_packet("join_game", *join_game)

    # Sends a signed chat message to supporting clients
    def broadcast_signed_chat(self, message: SignedMessage, sender_name):
        for player in self.players:
            if player.protocol_mode != 'play':
                continue

            # Only send signed messages to clients that support the same signing method
            if message.signature_version == player.protocol_version:
                self.send_signed_chat(player, message, sender_name)
            else:
                self.send_unsigned_chat(player, message.body.message, message.header.sender, sender_name)

    def send_signed_chat(self, player: ChatRoomProtocol, message: SignedMessage, sender_name):
        # Add to player's pending messages for later last seen validation
        if self.online_mode:
            player.pending_messages.append(LastSeenMessage(message.header.sender, message.signature))

        if player.protocol_version >= 760:
            player.send_packet("chat_message",
                               player.buff_type.pack_signed_message(message),
                               player.buff_type.pack_varint(0),  # Chat filtering result, 0 = not filtered
                               player.buff_type.pack_varint(0),  # Message type
                               player.buff_type.pack_chat(sender_name),  # Sender display name
                               player.buff_type.pack('?', False))  # No team name

        # 1.19 packet format is different
        else:
            player.send_packet("chat_message",
                               player.buff_type.pack_chat(message.body.message),  # Original message
                               # Optional decorated message
                               player.buff_type.pack_optional(player.buff_type.pack_chat,
                                                              message.body.decorated_message),
                               player.buff_type.pack_varint(0),  # Message type, 0 = chat
                               player.buff_type.pack_uuid(message.header.sender),  # Sender UUID
                               player.buff_type.pack_chat(sender_name),  # Sender display name
                               player.buff_type.pack('?', False),  # Optional team name
                               # Timestamp, salt
                               player.buff_type.pack('QQ', message.body.timestamp, message.body.salt),
                               player.buff_type.pack_byte_array(message.signature or b''))  # Signature

    # Sends an unsigned chat message, using system messages on supporting clients
    def broadcast_unsigned_chat(self, message: str, sender: UUID, sender_name: str):
        for player in self.players:
            if player.protocol_mode != 'play':
                continue

            self.send_unsigned_chat(player, message, sender, sender_name)

    def send_unsigned_chat(self, player: ChatRoomProtocol, message: str, sender: UUID, sender_name: str):
        # 1.19+ Send as system message to avoid client signature warnings
        if player.protocol_version >= 759:
            self.send_system(player, "<%s> %s" % (sender_name, message))
        else:  # Send regular chat message
            player.send_packet("chat_message",
                               player.buff_type.pack_chat("<%s> %s" % (sender_name, message)),
                               player.buff_type.pack('B', 0),
                               player.buff_type.pack_uuid(sender))

    # Sends a system message, falling back to chat messages on older clients
    def broadcast_system(self, message: str):
        for player in self.players:
            if player.protocol_mode != 'play':
                continue

            self.send_system(player, message)

    @staticmethod
    def send_system(player: ChatRoomProtocol, message: str):
        if player.protocol_version >= 760:  # 1.19.1+
            player.send_packet("system_message",
                               player.buff_type.pack_chat(message),
                               player.buff_type.pack('?', False))  # Overlay, false = display in chat
        elif player.protocol_version == 759:  # 1.19
            player.send_packet("system_message",
                               player.buff_type.pack_chat(message),
                               player.buff_type.pack_varint(1))
        else:
            player.send_packet("chat_message",
                               player.buff_type.pack_chat(message),
                               player.buff_type.pack('B', 0),
                               player.buff_type.pack_uuid(UUID(int=0)))

    # Announces player join
    def broadcast_player_join(self, joined: ChatRoomProtocol):
        self.broadcast_system("\u00a7e%s has joined." % joined.display_name)
        self.broadcast_player_list_add(joined)

    # Announces player leave
    def broadcast_player_leave(self, left: ChatRoomProtocol):
        self.broadcast_system("\u00a7e%s has left." % left.display_name)
        self.broadcast_player_list_remove(left)

    # Sends player list entry for new player to other players
    def broadcast_player_list_add(self, added: ChatRoomProtocol):
        for player in self.players:
            # Exclude the added player, they will be sent the full player list separately
            if player.protocol_mode == 'play' and player != added:
                self.send_player_list_add(player, [added])

    @staticmethod
    def send_player_list_add(player: ChatRoomProtocol, added: List[ChatRoomProtocol]):
        data = [
            player.buff_type.pack_varint(0),  # Action - 0 = Player add
            player.buff_type.pack_varint(len(added)),  # Player entry count
        ]

        for entry in added:
            if entry.protocol_mode != 'play':
                continue

            data.append(player.buff_type.pack_uuid(entry.uuid))  # Player UUID
            data.append(player.buff_type.pack_string(entry.display_name))  # Player name
            data.append(player.buff_type.pack_varint(0))  # Empty properties list
            data.append(player.buff_type.pack_varint(3))  # Gamemode
            data.append(player.buff_type.pack_varint(0))  # Latency
            data.append(player.buff_type.pack('?', False))  # No display name

            # Add signature for 1.19+ clients if it exists
            if player.protocol_version >= 759:
                data.append(player.buff_type.pack_optional(player.buff_type.pack_player_public_key, entry.public_key_data))

        player.send_packet('player_list_item', *data)

    # Sends player list update for leaving player to other players
    def broadcast_player_list_remove(self, removed: ChatRoomProtocol):
        for player in self.players:
            if player.protocol_mode == 'play' and player != removed:
                player.send_packet('player_list_item',
                                   player.buff_type.pack_varint(4),  # Action - 4 = Player remove
                                   player.buff_type.pack_varint(1),  # Player entry count
                                   player.buff_type.pack_uuid(removed.uuid))  # Player UUID


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
