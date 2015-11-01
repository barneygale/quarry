import sys

from quarry.net.items import items

PY3 = sys.version_info > (3,)
if PY3:
    string_type = str
else:
    string_type = unicode

def dump_string(obj):
    if isinstance(obj, dict):
        return "{%s}" % ",".join("%s: %s" % (key, dump_string(value)) for key, value in obj.items()
                                 if value is not None)
    elif isinstance(obj, list):
        return "[%s]" % ",".join(dump_string(elem) for elem in obj)
    elif isinstance(obj, string_type):
        return "%s" % obj.encode('utf8')
    else:
        return "%s" % obj

def dump_slots(slots):
    parts = []
    for i, slot in enumerate(slots):
        if slot['id'] != -1:
            part = {
                'id': items[slot['id']],
                'Damage': slot['damage'],
                'Count': slot['count'],
                'Slot': i}
            if slot['tag'] is not None:
                part['tag'] = slot['tag'][1]

            parts.append(part)

    return dump_string(parts)