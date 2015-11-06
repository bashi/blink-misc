import base64
import json
import zlib
import re
import sys


def _get_viewer_data(html_contents):
    m = re.search(
        r'<script id="viewer-data" type="application/json">\n(.*)\n</script>',
        html_contents)
    return m.group(1)


def get_trace_data(html_contents):
    viewer_data = _get_viewer_data(html_contents)
    compressed = base64.b64decode(viewer_data)
    raw_data = zlib.decompress(compressed, zlib.MAX_WBITS|32)
    trace_data = json.loads(raw_data)
    return trace_data


def main(args):
    with open(args[0]) as f:
        trace_data = get_trace_data(f.read())
        print(json.dumps(trace_data, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
