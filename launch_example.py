import os, imp

def main(args):
    if len(args) == 0:
        print "usage: python launch_example.py <example_name> [args...]"
        return

    example_name = args.pop(0)
    example_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "examples",
        "%s.py" % example_name)

    if not os.path.exists(example_path):
        print "example not found: %s" % example_name
        return

    example_mod = imp.load_source(example_name, example_path)
    example_mod.main(args)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])