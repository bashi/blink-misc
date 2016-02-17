import glob
import json
import os
import sys

from util.read_trace import read_trace
from util.scoped_chdir import scoped_chdir


def convert(directory):
    """Convert all telemetry benchmark results in a given directory to JSON."""
    directory = os.path.abspath(directory)
    with scoped_chdir(directory):
        for html in glob.glob('*.html'):
            trace = read_trace(html)
            filename = os.path.splitext(html)[0] + '.json'
            with open(filename, 'w') as f:
                f.write(json.dumps(trace, indent=2))


def main(args):
    convert(args[0])


if __name__ == '__main__':
    main(sys.argv[1:])
