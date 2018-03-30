class BufferUnderrun(Exception):
    pass


from quarry.types.buffer.v1_7 import Buffer1_7
from quarry.types.buffer.v1_9 import Buffer1_9


# Versioned buffers used after handshaking
buff_types = [
    (0,   Buffer1_7),
    (107, Buffer1_9),
]


# Used by NBT and during handshaking
class Buffer(Buffer1_9):
    pass
