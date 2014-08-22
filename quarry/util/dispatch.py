import string

# Registers a packet handler by giving it a '_packet_handler' field
def register(*lookup_args):
    def inner(fnc):
        fnc._packet_handler = lookup_args
        return fnc
    return inner

class PacketDispatcher(object):
    def register_handlers(self):
        self.packet_handlers = {}

        for field_name in dir(self): #TODO: was cls
            if not field_name.startswith("__"):
                handler     = getattr(self, field_name)
                lookup_args = getattr(handler, "_packet_handler", None)
                if lookup_args:
                    self.packet_handlers[lookup_args] = field_name

    def dispatch(self, lookup_args, buff):
        handler = self.packet_handlers.get(lookup_args, None)
        if handler is not None:
            getattr(self, handler)(buff)
            return True
        return False

    def dump_packet(self, data):
        lines = ['Packet dump:']
        bytes_read = 0
        while len(data) > 0:
            data_line, data = data[:16], data[16:]

            l_hex = []
            l_str = []
            for c in data_line:
                l_hex.append("%02x" % ord(c))
                l_str.append(c if c in string.printable else ".")

            l_hex.extend(['  ']*(16-len(l_hex)))
            l_hex.insert(8,'')


            lines.append("%08x  %s  |%s|" % (
                bytes_read,
                " ".join(l_hex),
                "".join(l_str)))

            bytes_read += len(data_line)

        return "\n    ".join(lines + ["%08x" % bytes_read])
