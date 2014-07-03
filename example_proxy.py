from quarry.net.proxy import ProxyServerFactory

###
### PROXY SERVER
###   Proxy support is not finished yet!
###


def main():
    # Parse options
    import optparse
    parser = optparse.OptionParser("usage: %prog [options] connect-host connect-port")
    parser.add_option("-a", "--listen-host",
                      dest="listen_host", default="",
                      help="address to listen on")
    parser.add_option("-p", "--listen-port",
                      dest="listen_port", default="25565", type="int",
                      help="port to listen on")
    (options, args) = parser.parse_args()

    if len(args) != 2:
        return parser.print_usage()

    # Create factory
    factory = ProxyServerFactory()
    factory.motd = "Proxy Server"
    factory.connect_host = args[0]
    factory.connect_port = int(args[1])

    # Listen
    factory.listen(options.listen_host, options.listen_port)
    factory.run()

if __name__ == "__main__":
    main()