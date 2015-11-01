import os.path
import csv

def _load():
    items = {}
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
            items[item_id] = item_name

    return items

items = _load()
