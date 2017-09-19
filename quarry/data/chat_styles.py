def _load():
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

code_by_name, code_by_prop = _load()