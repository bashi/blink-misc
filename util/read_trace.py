import base64
import gzip
import json
import zlib
import re
import os
import sys


def _get_viewer_data(html_contents):
    m = re.search(
        r'<script id="viewer-data" type="application/json">\n(.*)\n</script>',
        html_contents)
    return m.group(1)


def get_trace_data_from_html(html_contents):
    viewer_data = _get_viewer_data(html_contents)
    compressed = base64.b64decode(viewer_data)
    raw_data = zlib.decompress(compressed, zlib.MAX_WBITS|32)
    trace_data = json.loads(raw_data)
    return trace_data


def read_trace(filename):
    _, ext = os.path.splitext(filename)
    if ext == '.json':
        with open(filename) as f:
            return json.load(f)
    elif ext == '.html':
        with open(filename) as f:
            return get_trace_data_from_html(f.read())
    elif ext == '.gz':
        with gzip.open(filename, 'rb') as f:
            return json.load(f)
    else:
        raise Exception('Unsupported format: ' + ext)


def main(args):
    trace_data = read_trace(args[0])
    print(json.dumps(trace_data, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
