class BufferUnderrun(Exception):
    pass


from quarry.types.buffer.v1_7 import Buffer1_7
from quarry.types.buffer.v1_9 import Buffer1_9
from quarry.types.buffer.v1_13 import Buffer1_13
from quarry.types.buffer.v1_13_2 import Buffer1_13_2


# Versioned buffers used after handshaking
buff_types = [
    (0,   Buffer1_7),
    (107, Buffer1_9),
    (393, Buffer1_13),
    (404, Buffer1_13_2),
]


# Used by NBT and during handshaking
class Buffer(buff_types[-1][1]):
    pass
