class BufferUnderrun(Exception):
    pass


from quarry.types.buffer.v1_7 import Buffer1_7
from quarry.types.buffer.v1_9 import Buffer1_9
from quarry.types.buffer.v1_13 import Buffer1_13
from quarry.types.buffer.v1_13_2 import Buffer1_13_2
from quarry.types.buffer.v1_14 import Buffer1_14
from quarry.types.buffer.v1_19 import Buffer1_19
from quarry.types.buffer.v1_19_1 import Buffer1_19_1
from quarry.types.buffer.v1_20_4 import Buffer1_20_4

# Versioned buffers used after handshaking
buff_types = [
    (0,   Buffer1_7),
    (107, Buffer1_9),
    (393, Buffer1_13),
    (404, Buffer1_13_2),
    (477, Buffer1_14),
    (759, Buffer1_19),
    (760, Buffer1_19_1),
    (765, Buffer1_20_4),
]


# Used by NBT and during handshaking
class Buffer(buff_types[-1][1]):
    pass
