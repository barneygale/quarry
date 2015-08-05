import string

class PacketDispatcher(object):
    def dispatch(self, lookup_args, buff):
        handler = getattr(self, "packet_%s" % "_".join(lookup_args), None)
        if handler is not None:
            handler(buff)
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
