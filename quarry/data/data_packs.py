import glob
import os.path
import re

from quarry.types.nbt import NBTFile, TagRoot


def _load():
    data_packs = {}
    dimension_types = {}
    nbt_paths = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "data_packs",
        "*.nbt"))
    for nbt_path in glob.glob(nbt_paths):
        match = re.match('(\d{4})_(.+)\.nbt', os.path.basename(nbt_path))
        if not match:
            continue

        protocol_version = int(match.group(1))
        minecraft_version = match.group(2)
        data_pack = NBTFile.load(nbt_path).root_tag

        data_packs[protocol_version] = data_pack

        for entry in data_pack.body.value.values():
            if entry.value['type'].value == 'minecraft:dimension_type':
                for dimension in entry.value['value'].value:
                    name = dimension.value['name'].value
                    value = TagRoot.from_body(dimension.value['element'])
                    dimension_types[protocol_version, name] = value

    return data_packs, dimension_types


data_packs, dimension_types = _load()
