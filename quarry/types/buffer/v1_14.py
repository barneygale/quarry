from quarry.types.chunk import BlockArray
from quarry.types.buffer.v1_13_2 import Buffer1_13_2

poses = ('standing', 'fall_flying', 'sleeping', 'swimming', 'spin_attack',
         'sneaking', 'dying')
smelt_types = ('minecraft:smelting', 'minecraft:blasting',
               'minecraft:smoking', 'minecraft:campfire_cooking')

class Buffer1_14(Buffer1_13_2):

    # Chunk section -----------------------------------------------------------

    @classmethod
    def pack_chunk_section(cls, blocks, block_lights=None, sky_lights=None):
        """
        Packs a chunk section. The supplied argument should be an instance of
        ``quarry.types.chunk.BlockArray``.
        """

        out = cls.pack('HB', blocks.non_air, blocks.storage.value_width)
        out += cls.pack_chunk_section_palette(blocks.palette)
        out += cls.pack_chunk_section_array(blocks.to_bytes())
        return out

    def unpack_chunk_section(self, overworld=True):
        """
        Unpacks a chunk section. Returns a sequence of length 4096 (16x16x16).
        """

        non_air, value_width = self.unpack('HB')
        palette = self.unpack_chunk_section_palette(value_width)
        array = self.unpack_chunk_section_array(value_width)
        return BlockArray.from_bytes(
            bytes=array,
            palette=palette,
            registry=self.registry,
            non_air=non_air,
            value_width=value_width), None, None

    # Position ----------------------------------------------------------------

    @classmethod
    def pack_position(cls, x, y, z):
        """
        Packs a Position.
        """

        def pack_twos_comp(bits, number):
            if number < 0:
                number = number + (1 << bits)
            return number

        return cls.pack('Q', sum((
            pack_twos_comp(26, x) << 38,
            pack_twos_comp(26, z) << 12,
            pack_twos_comp(12, y))))

    def unpack_position(self):
        """
        Unpacks a position.
        """

        def unpack_twos_comp(bits, number):
            if (number & (1 << (bits - 1))) != 0:
                number = number - (1 << bits)
            return number

        number = self.unpack('Q')
        x = unpack_twos_comp(26, (number >> 38))
        z = unpack_twos_comp(26, (number >> 12 & 0x3FFFFFF))
        y = unpack_twos_comp(12, (number & 0xFFF))
        return x, y, z


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
            elif ty == 8:  out += cls.pack_rotation(*val)
            elif ty == 9:  out += cls.pack_position(*val)
            elif ty == 10: out += cls.pack_optional(pack_position, val)
            elif ty == 11: out += cls.pack_direction(val)
            elif ty == 12: out += cls.pack_optional(cls.pack_uuid, val)
            elif ty == 13: out += cls.pack_block(val)
            elif ty == 14: out += cls.pack_nbt(val)
            elif ty == 15: out += cls.pack_particle(*val)
            elif ty == 16: out += cls.pack_villager(*val)
            elif ty == 17: out += cls.pack_optional_varint(val)
            elif ty == 18: out += cls.pack_pose(val)
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
            elif ty == 8:  val = self.unpack_rotation()
            elif ty == 9:  val = self.unpack_position()
            elif ty == 10: val = self.unpack_optional(self.unpack_position)
            elif ty == 11: val = self.unpack_direction()
            elif ty == 12: val = self.unpack_optional(self.unpack_uuid)
            elif ty == 13: val = self.unpack_block()
            elif ty == 14: val = self.unpack_nbt()
            elif ty == 15: val = self.unpack_particle()
            elif ty == 16: val = self.unpack_villager()
            elif ty == 17: val = self.unpack_optional_varint()
            elif ty == 18: val = self.unpack_pose()
            else: raise ValueError("Unknown entity metadata type: %d" % ty)
            metadata[ty, key] = val

    # Particle ----------------------------------------------------------------

    @classmethod
    def pack_particle(cls, kind, data=None):
        """
        Packs a particle.
        """

        id = cls.registry.encode('minecraft:particle_type', kind)
        return super(Buffer1_14, cls).pack_particle(id, data)


    def unpack_particle(self):
        """
        Unpacks a particle. Returns an ``(kind, data)`` pair.
        """

        id, data = super(Buffer1_14, self).unpack_particle()
        kind = self.registry.decode('minecraft:particle_type', id)
        return kind, data


    # Villager data -----------------------------------------------------------

    @classmethod
    def pack_villager(cls, kind, profession, level):
        """
        Packs villager data.
        """

        kind = cls.registry.encode('minecraft:villager_type', kind)
        profession = cls.registry.encode('minecraft:villager_profession', profession)
        return cls.pack_varint(kind) + \
               cls.pack_varint(profession) + \
               cls.pack_varint(level)

    def unpack_villager(self):
        """
        Unpacks villager data.
        """
        kind = self.registry.decode(
            'minecraft:villager_type', self.unpack_varint())
        profession = self.registry.decode(
            'minecraft:villager_profession', self.unpack_varint())
        level = self.unpack_varint()
        return kind, profession, level


    # Optional varint ---------------------------------------------------------

    @classmethod
    def pack_optional_varint(cls, number):
        """
        Packs an optional varint.
        """

        return cls.pack_varint(0 if number is None else number + 1)

    def unpack_optional_varint(self):
        """
        Unpacks an optional varint.
        """

        val = self.unpack_varint()
        if val == 0:
            return None
        else:
            return val - 1


    # Pose --------------------------------------------------------------------

    @classmethod
    def pack_pose(cls, pose):
        """
        Packs a pose.
        """

        return cls.pack_varint(poses.index(pose))

    def unpack_pose(self):
        """
        Unpacks a pose.
        """

        return poses[self.unpack_varint()]

    # Recipes -----------------------------------------------------------------

    def unpack_recipe(self):
        """
        Unpacks a crafting recipe.
        """
        recipe = {}
        recipe['type'] = self.unpack_string()
        recipe['name'] = self.unpack_string()

        if recipe['type'] == 'minecraft:crafting_shapeless':
            recipe['group'] = self.unpack_string()
            recipe['ingredients'] = [
                self.unpack_ingredient() for _ in range(self.unpack_varint())]
            recipe['result'] = self.unpack_slot()

        elif recipe['type'] == 'minecraft:crafting_shaped':
            recipe['width'] = self.unpack_varint()
            recipe['height'] = self.unpack_varint()
            recipe['group'] = self.unpack_string()
            recipe['ingredients'] = [
                self.unpack_ingredient() for _ in range(recipe['width'] *
                                                    recipe['height'])]
            recipe['result'] = self.unpack_slot()
        elif recipe['type'] in smelt_types:
            recipe['group'] = self.unpack_string()
            recipe['ingredient'] = self.unpack_ingredient()
            recipe['result'] = self.unpack_slot()
            recipe['experience'] = self.unpack('f')
            recipe['cooking_time'] = self.unpack_varint()

        return recipe

    @classmethod
    def pack_recipe(cls, name, type, **recipe):
        """
        Packs a crafting recipe.
        """
        data = cls.pack_string(type) + cls.pack_string(name)

        if type == 'minecraft:crafting_shapeless':
            data += cls.pack_string(recipe['group'])
            data += cls.pack_varint(len(recipe['ingredients']))
            for ingredient in recipe['ingredients']:
                data += cls.pack_ingredient(ingredient)
            data += cls.pack_slot(**recipe['result'])

        elif type == 'minecraft:crafting_shaped':
            data += cls.pack_varint(recipe['width'])
            data += cls.pack_varint(recipe['height'])
            data += cls.pack_string(recipe['group'])
            for ingredient in recipe['ingredients']:
                data += cls.pack_ingredient(ingredient)
            data += cls.pack_slot(**recipe['result'])

        elif type in smelt_types:
            data += cls.pack_string(recipe['group'])
            data += cls.pack_ingredient(recipe['ingredient'])
            data += cls.pack_slot(**recipe['result'])
            data += cls.pack('f', recipe['experience'])
            data += cls.pack_varint(recipe['cooking_time'])

        return data
