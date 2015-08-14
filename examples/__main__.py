from __future__ import print_function
import os

if __name__ == '__main__':
    print("Examples:")
    for filename in sorted(os.listdir(os.path.dirname(__file__))):
        name, ext = os.path.splitext(filename)
        if ext == '.py' and name[0] != '_':
            print("- examples.%s" % name)
