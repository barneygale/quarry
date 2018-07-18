from quarry.types.buffer.v1_9 import Buffer1_9
from quarry.types.block import OpaqueBlockMap

# Python 3 compat
try:
    xrange
except NameError:
    xrange = range


class Buffer1_13(Buffer1_9):
    block_map = OpaqueBlockMap(14)

    # Chunk section -----------------------------------------------------------


    @classmethod
    def pack_chunk_section_palette(cls, palette):
        if not palette:
            return b""
        else:
            return cls.pack_varint(len(palette)) + b"".join(
                cls.pack_varint(x) for x in palette)

    def unpack_chunk_section_palette(self, bits):
        if bits > 8:
            return []
        else:
            return [self.unpack_varint() for _ in xrange(self.unpack_varint())]

    # Slot --------------------------------------------------------------------

    @classmethod
    def pack_slot(cls, item=None, count=1, tag=None):
        """
        Packs a slot.
        """

        if item is None:
            return cls.pack('h', -1)

        item_id = cls.block_map.encode_item(item)
        return cls.pack('hb', item_id, count) + cls.pack_nbt(tag)

    def unpack_slot(self):
        """
        Unpacks a slot.
        """

        slot = {}
        item_id = self.unpack('h')
        if item_id == -1:
            slot['item'] = None
        else:
            slot['item'] = self.block_map.decode_item(item_id)
            slot['count'] = self.unpack('b')
            slot['tag'] = self.unpack_nbt()
        return slot

    # Entity metadata ---------------------------------------------------------

    @classmethod
    def pack_entity_metadata(cls, metadata):
        """
        Packs entity metadata.
        """

        pack_position = lambda pos: cls.pack_position(*pos)
        out = b""
        for ty_key, val in metadata.items():
            ty, key = ty_key
            out += cls.pack('BB', key, ty)
            if   ty == 0:  out += cls.pack('b', val)
            elif ty == 1:  out += cls.pack_varint(val)
            elif ty == 2:  out += cls.pack('f', val)
            elif ty == 3:  out += cls.pack_string(val)
            elif ty == 4:  out += cls.pack_chat(val)
            elif ty == 5:  out += cls.pack_optional(cls.pack_chat, val)
            elif ty == 6:  out += cls.pack_slot(**val)
            elif ty == 7:  out += cls.pack('?', val)
            elif ty == 8:  out += cls.pack('fff', *val)
            elif ty == 9:  out += cls.pack_position(*val)
            elif ty == 10: out += cls.pack_optional(pack_position, val)
            elif ty == 11: out += cls.pack_varint(val)
            elif ty == 12: out += cls.pack_optional(cls.pack_uuid, val)
            elif ty == 13: out += cls.pack_block(val)
            elif ty == 14: out += cls.pack_nbt(val)
            elif ty == 15: out += cls.pack_particle(*val)
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
        out += cls.pack('B', 255)
        return out

    def unpack_entity_metadata(self):
        """
        Unpacks entity metadata.
        """

        metadata = {}
        while True:
            key = self.unpack('B')
            if key == 255:
                return metadata
            ty = self.unpack('B')
            if   ty == 0:  val = self.unpack('b')
            elif ty == 1:  val = self.unpack_varint()
            elif ty == 2:  val = self.unpack('f')
            elif ty == 3:  val = self.unpack_string()
            elif ty == 4:  val = self.unpack_chat()
            elif ty == 5:  val = self.unpack_optional(self.unpack_chat)
            elif ty == 6:  val = self.unpack_slot()
            elif ty == 7:  val = self.unpack('?')
            elif ty == 8:  val = self.unpack('fff')
            elif ty == 9:  val = self.unpack_position()
            elif ty == 10: val = self.unpack_optional(self.unpack_position)
            elif ty == 11: val = self.unpack_varint()
            elif ty == 12: val = self.unpack_optional(self.unpack_uuid)
            elif ty == 13: val = self.unpack_block()
            elif ty == 14: val = self.unpack_nbt()
            elif ty == 15: val = self.unpack_particle()
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata[ty, key] = val

    # Particle ----------------------------------------------------------------

    @classmethod
    def pack_particle(cls, id, data=None):
        """
        Packs a particle.
        """
        data = data or {}
        out = cls.pack_varint(id)
        if id == 3 or id == 20:
            out += cls.pack_varint(data['block_state'])
        elif id == 11:
            out += cls.pack(
                'ffff',
                data['red'],
                data['green'],
                data['blue'],
                data['scale'])
        elif id == 27:
            out += cls.pack_slot(**data['item'])

    def unpack_particle(self):
        """
        Unpacks a particle. Returns an ``(id, data)`` pair.
        """
        id = self.unpack_varint()
        if id == 3 or id == 20:
            data = {'block_state': self.unpack_varint()}
        elif id == 11:
            data = dict(zip(
                ('red', 'green', 'blue', 'scale'),
                self.unpack('ffff')))
        elif id == 27:
            data = {'item': self.unpack_slot()}
        else:
            data = {}

        return id, data

    # Commands ----------------------------------------------------------------

    def unpack_commands(self, resolve_redirects=True):
        """
        Unpacks a command graph.

        If *resolve_redirects* is ``True`` (the default), the returned
        structure may contain contain circular references, and therefore cannot
        be serialized to JSON (or similar). If it is ``False``, all node
        redirect information is stripped, resulting in a directed acyclic
        graph.
        """

        # Unpack nodes
        node_count = self.unpack_varint()
        nodes = [self.unpack_command_node() for _ in range(node_count)]

        # Resolve children and redirects
        for node in nodes:
            node['children'] = {nodes[idx]['name']: nodes[idx]
                                for idx in node['children']}
            if node['redirect'] is not None:
                if resolve_redirects:
                    node['redirect'] = nodes[node['redirect']]
                else:
                    node['redirect'] = None

        return nodes[self.unpack_varint()]

    def unpack_command_node(self):
        """
        Unpacks a command node.
        """

        node = {}

        flags = self.unpack('B')
        node['type'] = ['root', 'literal', 'argument'][flags & 0x03]
        node['executable'] = bool(flags & 0x04)
        node['children'] = [self.unpack_varint() for _ in
                            range(self.unpack_varint())]
        node['redirect'] = self.unpack_varint() if flags & 0x08 else None
        node['name'] = self.unpack_string() if node['type'] != 'root' else None

        if node['type'] == 'argument':
            node['parser'] = self.unpack_string()
            node['properties'] = self.unpack_command_node_properties(node['parser'])

        node['suggestions'] = self.unpack_string() if flags & 0x10 else None

        return node

    def unpack_command_node_properties(self, parser):
        """
        Unpacks the properties of an ``argument`` command node.
        """

        namespace, parser = parser.split(":", 1)
        properties = {}

        if namespace == "brigadier":
            if parser == "bool":
                pass
            elif parser == "string":
                properties['behavior'] = self.unpack_varint()
            elif parser in ("double", "float", "integer"):
                fmt = parser[0]
                flags = self.unpack('B')
                properties['min'] = self.unpack(fmt) if flags & 0x01 else None
                properties['max'] = self.unpack(fmt) if flags & 0x02 else None

        elif namespace == "minecraft":
            if parser in ('entity', 'score_holder'):
                properties['allow_multiple'] = self.unpack('?')

            elif parser == 'range':
                properties['allow_decimals'] = self.unpack('?')

        return properties

    @classmethod
    def pack_commands(cls, root_node):
        """
        Packs a command graph.
        """

        # Enumerate nodes
        nodes = [root_node]
        idx = 0
        while idx < len(nodes):
            children = nodes[idx]['children'].values()
            for child in children:
                if child not in nodes:
                    nodes.append(child)
            idx += 1

        # Pack nodes
        out = cls.pack_varint(len(nodes))
        for node in nodes:
            out += cls.pack_command_node(node, nodes)

        out += cls.pack_varint(nodes.index(root_node))

        return out

    @classmethod
    def pack_command_node(cls, node, nodes):
        """
        Packs a command node.
        """

        out = b""

        flags = (
            ['root', 'literal', 'argument'].index(node['type']) |
            int(node['executable']) << 2 |
            int(node['redirect'] is not None) << 3 |
            int(node['suggestions'] is not None) << 4)
        out += cls.pack('B', flags)
        out += cls.pack_varint(len(node['children']))

        for child in node['children'].values():
            out += cls.pack_varint(nodes.index(child))

        if node['redirect'] is not None:
            out += cls.pack_varint(nodes.index(node['redirect']))

        if node['name'] is not None:
            out += cls.pack_string(node['name'])

        if node['type'] == 'argument':
            out += cls.pack_string(node['parser'])
            out += cls.pack_command_node_properties(node['parser'],
                                                    node['properties'])
        if node['suggestions'] is not None:
            out += cls.pack_string(node['suggestions'])

        return out

    @classmethod
    def pack_command_node_properties(cls, parser, properties):
        """
        Packs the properties of an ``argument`` command node.
        """

        namespace, parser = parser.split(":", 1)
        out = b""

        if namespace == "brigadier":
            if parser == "bool":
                pass
            elif parser == "string":
                out += cls.pack_varint(properties['behavior'])
            elif parser in ("double", "float", "integer"):
                fmt = parser[0]
                flags = (
                    int(properties['min'] is not None) |
                    int(properties['max'] is not None) << 1)
                out += cls.pack('B', flags)
                if properties['min'] is not None:
                    out += cls.pack(fmt, properties['min'])
                if properties['max'] is not None:
                    out += cls.pack(fmt, properties['max'])

        elif namespace == "minecraft":
            if parser in ('entity', 'score_holder'):
                out += cls.pack('?', properties['allow_multiple'])

            elif parser == 'range':
                out += cls.pack('?', properties['allow_decimals'])

        return out