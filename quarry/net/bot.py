import re
from twisted.internet.protocol import ReconnectingClientFactory

from quarry.net.client import ClientFactory, ClientProtocol, register

# exception





class BotProtocol(ClientProtocol):
    protocol_mode_next = "login"

    chat_message_interval = 1.0
    chat_throttle_length = 3.0

    command_prefix = "!"

    #-- SETUP -----------------------------------------------------------------

    def setup(self):
        self.on_ground = False

        self.spawned = False

        self.chat_throttled = False
        self.pending_chat = []

        self.register_chat_handlers()

    def register_chat_handlers(self):
        self.command_handlers = [] # command, callback
        self.chat_handlers = [] # regex, callback
        self.raw_handlers = [] # regex, callbac

    #-- LOOPS/TASKS -----------------------------------------------------------

    def update_position(self):
        self.send_packet(0x03,
            self.buff_type.pack('?', self.on_ground))

    def update_chat(self):
        if len(self.pending_chat) > 0:
            message = self.pending_chat.pop(0)
            self.send_packet(0x01,
                self.buff_type.pack_string(message))

    #-- CHAT HELPERS ----------------------------------------------------------

    def throttle_chat(self):
        if not self.chat_throttled:
            self.chat_throttled = True

            def unthrottle_chat():
                self.chat_throttled = False

            self.tasks.add_delay(self.chat_throttle_length, unthrottle_chat)

    def send_chat(self, message, prefix=""):
        max_length = 100 - len(prefix)
        lines = message.split("\n")
        while len(lines) > 0:
            line = lines.pop(0).strip()
            if not line:
                continue
            if len(line) > max_length:
                split_pos = line.rfind(" ", 0, max_length+1)
                if split_pos == -1:
                    split_pos = 0
                line, extra = line[:split_pos], line[split_pos+1:]

                lines.insert(0, extra)

            self.pending_chat.append(prefix+line)

    def send_whisper(self, message, player):
        self.send_chat(message, "/tell %s " % player)

    #-- CHAT PARSERS ----------------------------------------------------------

    def parse_command(self, text):
        command_regex = re.escape(self.command_prefix) + '([a-z]+)\s?(.*)'
        whispered = False
        match = re.match('<([0-9A-Za-z_]{1,16})>\s' + command_regex, text)
        if match is None:
            match = re.match('([0-9A-Za-z_]{1,16})\swhisper(?:ed|s):?\s' + command_regex, text)
            if match is None:
                return None
            whispered = True

        player, command, args = match.groups()
        return whispered, player, command, args

    def parse_chat(self, text):
        match = re.match('<([0-9A-Za-z_]{1,16})>\s(.+)', text)
        if match is None:
            return None
        return match.groups()

    #-- PACKET HANDLERS -------------------------------------------------------

    @register("play", 0x02)
    def packet_chat_message(self, buff):
        p_text = buff.unpack_chat()

        self.logger.info(p_text)

        # Check for commands
        zzyzz = self.parse_command(p_text)
        if zzyzz:
            whispered, player, command, args = zzyzz
            for t_command, t_callback in self.command_handlers:
                if command == t_command:
                    t_callback(whispered, player, args)

        # Check for chat
        zzyzz = self.parse_chat(p_text)
        if zzyzz:
            player, text = zzyzz
            for t_regex, t_callback in self.chat_handlers:
                match = t_regex.match(text)
                if match:
                    t_callback(player, *match.groups())

        # Check for raw
        for t_regex, t_callback in self.raw_handlers:
            match = t_regex.match(p_text)
            if match:
                t_callback(*match.groups())

    @register("play", 0x08)
    def packet_player_position_and_look(self, buff):
        p_coords = buff.unpack('ddd')
        p_look = buff.unpack('ff')
        p_on_ground = buff.unpack('?')

        self.on_ground = p_on_ground

        # Send Player Position And Look
        self.send_packet(0x06, self.buff_type.pack('ddddff?',
            p_coords[0],
            p_coords[1] - 1.62,
            p_coords[1],
            p_coords[2],
            p_look[0],
            p_look[1],
            p_on_ground))

        if not self.spawned:
            self.tasks.add_loop(1.0/20, self.update_position)
            self.tasks.add_loop(self.chat_message_interval, self.update_chat)
            self.spawned = True

    @register("play", 0x40)
    def packet_play_kick(self, buff):
        p_reason = buff.unpack_chat()
        self.logger.warn("Kicked: %s" % p_reason)

class BotFactory(ClientFactory, ReconnectingClientFactory):
    protocol = BotProtocol

    def buildProtocol(self, addr):
        self.resetDelay()
        return ClientFactory.buildProtocol(self, addr)