import csv
import re
import urllib2

# Used to filter out pre-netty protocols
MINIMUM_OLDID = 5486

# Patterns
REGEX_WIKISOURCE = '<textarea.+?>(.+?)</textarea>'
REGEX_VERSIONS = "'''{{Minecraft Wiki\|([0-9\.]+)}}'''\n" \
                 '.+?\| (\d+)\n' \
                 '.+?\| \[http://wiki.vg/' \
                 '(?:index.php\?title=Protocol&amp;|Protocol\?)' \
                 'oldid=(\d+) page\]'
REGEX_SECTIONS = '\n(?P<level>=+)\s*(.+?)\s*(?P=level)'


def download(page, oldid=None):
    url = "http://wiki.vg/index.php?title=%s&action=edit" % page
    if oldid is not None:
        url += "&oldid=%d" % oldid
    data = urllib2.urlopen(url).read()
    match = re.search(REGEX_WIKISOURCE, data, flags=re.DOTALL)
    return match.group(1)


def main():
    output = csv.writer(open("packets.csv", "w"))
    output.writerow(("minecraft_version", "protocol_version", "protocol_mode",
                     "packet_direction", "packet_ident", "packet_name"))

    # Download the "Protocol version numbers" page
    p_versions = download("Protocol_version_numbers")

    for version in re.findall(REGEX_VERSIONS, p_versions):
        minecraft_version = version[0]
        protocol_version = int(version[1])
        oldid = int(version[2])

        # Ignore pre-netty protocols (quarry doesn't support them)
        if oldid >= MINIMUM_OLDID:

            # Grab packets from the "Protocol" page
            for packet in get_packets(oldid):
                row = [minecraft_version, protocol_version]
                row.extend(packet)
                output.writerow(row)
                pass


def get_packets(oldid):
    # Nested wiki headings
    breadcrumbs = [None]*6

    # Download the "Protocol" page at the given revision
    p_protocol = download("Protocol", oldid)

    # Grab a list of sections, each with a heading and some content
    sections = re.split(REGEX_SECTIONS, p_protocol, flags=re.DOTALL)
    sections.pop(0)  # Discard content before first header

    while len(sections) > 0:
        heading_prefix = sections.pop(0)
        heading_name = sections.pop(0)
        content = sections.pop(0)

        # Update breadcrumbs
        breadcrumbs[len(heading_prefix)-2] = heading_name

        # Parse packets
        if heading_prefix == "====":
            # Extract packet ident
            match = re.search('\! Notes.+?0x([0-9a-zA-Z]{2})', content,
                              flags=re.DOTALL)
            ident = int(match.group(1), 16)

            # Extract protocol mode, direction and packet name
            protocol_mode = {
                "Handshaking": "init",
                "Status": "status",
                "Login": "login",
                "Play": "play"}[breadcrumbs[0]]
            direction = {
                "Serverbound": "upstream",
                "Clientbound": "downstream"}[breadcrumbs[1]]
            packet_name = re.sub('[^a-z]', '_', breadcrumbs[2].lower())

            # Ignore pre-netty ping packet
            if packet_name == "legacy_server_list_ping":
                continue

            yield protocol_mode, direction, ident, packet_name

if __name__ == '__main__':
    main()