import os.path
import csv

def _load():
    item_names = {}
    item_ids = {}
    csvpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "items.csv"))
    with open(csvpath) as csvfile:
        reader = csv.reader(csvfile)
        for i, record in enumerate(reader):
            # Skip header
            if i == 0: continue

            # Extract fields
            item_id = int(record[0])
            item_name = record[1]

            # Save
            item_names[item_id] = item_name
            item_ids[item_name] = item_id

    return item_names, item_ids

item_names, item_ids = _load()
