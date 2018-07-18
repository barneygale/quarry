import functools
import re

from quarry.types.buffer import Buffer

try:
    basestring
except NameError:
    basestring = str


def _load_styles():
    data = {
        "0": "black",
        "1": "dark_blue",
        "2": "dark_green",
        "3": "dark_aqua",
        "4": "dark_red",
        "5": "dark_purple",
        "6": "gold",
        "7": "gray",
        "8": "dark_gray",
        "9": "blue",
        "a": "green",
        "b": "aqua",
        "c": "red",
        "d": "light_purple",
        "e": "yellow",
        "f": "white",
        "k": "obfuscated",
        "l": "bold",
        "m": "strikethrough",
        "n": "underline",
        "o": "italic",
        "r": "reset",
    }

    code_by_name = {}
    code_by_prop = {}
    for code, name in data.items():
        code_by_name[name] = code
        if code in "klmnor":
            if name == "underline":
                prop = "underlined"
            else:
                prop = name
            code_by_prop[prop] = code

    return code_by_name, code_by_prop

code_by_name, code_by_prop = _load_styles()


@functools.total_ordering
class Message(object):
    """
    Represents a Minecraft chat message.
    """
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_buff(cls, buff):
        return cls(buff.unpack_json())

    def to_bytes(self):
        return Buffer.pack_json(self.value)

    @classmethod
    def from_string(cls, string):
        return cls({'text': string})

    def to_string(self, strip_styles=True):
        """
        Minecraft uses a JSON format to represent chat messages; this method
        retrieves a plaintext representation, optionally including styles
        encoded using old-school chat codes (U+00A7 plus one character).
        """

        def parse(obj):
            if isinstance(obj, basestring):
                return obj
            if isinstance(obj, list):
                return "".join((parse(e) for e in obj))
            if isinstance(obj, dict):
                text = ""
                for prop, code in code_by_prop.items():
                    if obj.get(prop):
                        text += u"\u00a7" + code
                if "color" in obj:
                    text += u"\u00a7" + code_by_name[obj["color"]]
                if "translate" in obj:
                    text += obj["translate"]
                    if "with" in obj:
                        args = u", ".join((parse(e) for e in obj["with"]))
                        text += u"{%s}" % args
                if "text" in obj:
                    text += obj["text"]
                if "extra" in obj:
                    text += parse(obj["extra"])
                return text

        text = parse(self.value)
        if strip_styles:
            text = self.strip_chat_styles(text)
        return text

    @classmethod
    def strip_chat_styles(cls, text):
        return re.sub(u"\u00A7.", "", text)

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        return self.to_string()
