
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
