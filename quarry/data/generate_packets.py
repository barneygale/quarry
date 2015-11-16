import sys
import csv
import re
import collections

PY3 = sys.version_info > (3,)
if PY3:
    import urllib.request
    urlread = lambda url: urllib.request.urlopen(url).read().decode('utf8')
else:
    import urllib2
    urlread = lambda url: urllib2.urlopen(url).read()

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

def markdown_title(text, underline):
    return "%s\n%s\n\n" % (text, underline*len(text))

def download(page, oldid=None):
    url = "http://wiki.vg/index.php?title=%s&action=edit" % page
    if oldid is not None:
        url += "&oldid=%d" % oldid
    data = urlread(url)
    match = re.search(REGEX_WIKISOURCE, data, flags=re.DOTALL)
    return match.group(1)


def main():
    output_csv = csv.writer(open("packets.csv", "w"))
    output_csv.writerow(("minecraft_version", "protocol_version",
                         "protocol_mode", "packet_direction", "packet_ident",
                         "packet_name"))
    output_rst = open("../../docs/packet_names.rst", "w")
    output_rst_packets = collections.defaultdict(list)
    output_rst_version = None


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
                protocol_mode, direction, ident, packet_name = packet
                # Write .csv
                output_csv.writerow([minecraft_version, protocol_version,
                                     protocol_mode, direction, ident,
                                     packet_name])

                # Collate for .rst
                if output_rst_version == None:
                    output_rst_version = minecraft_version
                if output_rst_version == minecraft_version:
                    output_rst_packets[packet_name].append(direction)

    # Write .rst
    output_rst.write(markdown_title("Packet Names", "="))
    output_rst.write("See the `Minecraft Coalition Wiki`_ for a details on "
                     "every packet.\n\n")
    output_rst.write(markdown_title("Minecraft %s" % output_rst_version, "-"))
    for full_name, modes in sorted(output_rst_packets.items()):
        output_rst.write("- ``%s`` (%s)\n" % (full_name, ", ".join(modes)))
    output_rst.write("\n")
    output_rst.write(".. _Minecraft Coalition Wiki: http://wiki.vg/Protocol")

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

            # Clean up login packet names
            if packet_name.startswith("login_"):
                packet_name = packet_name[6:]

            # Prepend mode to name
            if protocol_mode in ("login", "status"):
                packet_name  = '%s_%s' % (protocol_mode, packet_name)

            yield protocol_mode, direction, ident, packet_name

if __name__ == '__main__':
    main()