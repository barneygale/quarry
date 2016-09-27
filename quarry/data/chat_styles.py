import csv
import os

def _load():
    code_by_name = {}
    code_by_prop = {}
    csvpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "chat_styles.csv"))
    with open(csvpath) as csvfile:
        reader = csv.reader(csvfile)
        for i, record in enumerate(reader):
            # Skip header
            if i == 0: continue

            code, name, prop = record
            code_by_name[name] = code
            if prop:
                code_by_prop[prop] = code

    return code_by_name, code_by_prop

code_by_name, code_by_prop = _load()