import csv
import json
import sys

def main(args):
    if len(args) != 1:
        print("usage: python generate_items.py /path/to/burger-results.json")
        sys.exit(1)

    with open(args[0], 'r') as fd:
        data = json.load(fd)

    rows = {
        fields['numeric_id']: "minecraft:" + name
        for name, fields in
        data[0]['items']['item'].items() +
        data[0]['blocks']['block'].items()
    }

    with open("items.csv", "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(("id", "name"))
        csvwriter.writerows(sorted(rows.items()))

if __name__ == "__main__":
    main(sys.argv[1:])