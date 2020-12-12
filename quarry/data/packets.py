import csv
import glob
import os.path
import re


def _load():
    default_protocol_version = 0
    minecraft_versions = {}
    packet_names = {}
    packet_idents = {}
    csv_paths = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "packets",
        "*.csv"))
    for csv_path in glob.glob(csv_paths):
        match = re.match('(\d{4})_(.+)\.csv', os.path.basename(csv_path))
        if not match:
            continue

        protocol_version = int(match.group(1))
        minecraft_version = match.group(2)

        packet_ident = None
        last_section = None
        with open(csv_path) as csv_file:
            reader = csv.reader(csv_file)
            for i, record in enumerate(reader):
                # Skip header
                if i == 0:
                    continue

                # Extract fields
                protocol_mode = record[0]
                packet_direction = record[1]
                packet_name = record[2]

                section = (protocol_mode, packet_direction)
                if section != last_section:
                    packet_ident = 0
                last_section = section

                # Update default protocol version
                default_protocol_version = max(default_protocol_version,
                                               protocol_version)

                # Update minecraft versions
                minecraft_versions[protocol_version] = minecraft_version

                # Update the packet dictionaries
                key = [protocol_version, protocol_mode, packet_direction]
                packet_names[tuple(key + [packet_ident])] = packet_name
                packet_idents[tuple(key + [packet_name])] = packet_ident

                packet_ident += 1

    return (default_protocol_version, minecraft_versions,
            packet_names, packet_idents)

default_protocol_version, minecraft_versions, \
packet_names, packet_idents = _load()
