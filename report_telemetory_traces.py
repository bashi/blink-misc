import base64
import json
import hyou
from optparse import OptionParser
import time
import re
import sys
import zlib

# Prerequisite:
# 1. Install hyou
#    $ pip install --user hyou
# 2. Prepare credential and let bashi@ know your client id.
#    https://hyou.readthedocs.org/en/latest/#preparing-credentials
# 3. Apply https://codereview.chromium.org/1429153004
#
# Usage:
# 1. Run telemetry benchmark
#  $ mkdir /tmp/telemetry-traces
#  $ tools/perf/run_benchmark --output-format=json \
#      --output-dir=/tmp/telemetry-traces --pageset-repeat=1 \
#      --browser=android-chromium --device <device> --reset-results \
#      memory.blink_memory_mobile
# 2. Run this script
#  $ python report_telemetry_traces.py -c path/to/credential.json \
#      /tmp/telemetry-traces/results.json
# 3. Open the following URL.
#    https://docs.google.com/spreadsheets/d/1WZRpkrYG6KRbVWvey_3rf-LcHKAi7a444XaT0QqHfTw/edit#gid=0
#
#  (Omit -c option to dump results as JSON on console)

_PAT = r'<script id="viewer-data" type="application/json">\n(.*)\n</script>'
class HTMLTrace(object):
    def __init__(self, path=None):
        if path:
            with open(path) as f:
                self._html_contents = f.read()
            renderer_dump = self._get_renderer_dump()
            self.partitions = self._partitions_sizes(renderer_dump)
            self.partitions_allocated_sizes = self._partitions_allocated_objects_sizes(renderer_dump)
            self.partition_details = self._partition_alloc_details(renderer_dump)
        else:
            self.partitions = {}
            self.partition_details = {}

    def _get_viewer_data(self):
        pattern = re.compile(_PAT, re.MULTILINE)
        m = pattern.search(self._html_contents)
        return m.group(1)

    def _get_trace_data(self):
        viewer_data = self._get_viewer_data()
        compressed = base64.b64decode(viewer_data)
        raw_data = zlib.decompress(compressed, zlib.MAX_WBITS|32)
        result = json.loads(raw_data)
        return result

    def _get_renderer_pid(self, trace_data):
        # Assuming that the target renderer process is labeled.
        def filter_func(dump):
            return dump['name'] == 'process_labels'
        dumps = filter(filter_func, trace_data)
        assert(len(dumps) == 1)
        return dumps[0]['pid']

    def _find_explicit_dump(self, trace_data, pid):
        def filter_func(dump):
            return dump['name'] == 'explicitly_triggered' and dump['pid'] == pid
        dumps = filter(filter_func, trace_data)
        assert(len(dumps) == 1)
        return dumps[0]

    def _get_renderer_dump(self):
        trace_data = self._get_trace_data()
        pid = self._get_renderer_pid(trace_data)
        return self._find_explicit_dump(trace_data, pid)

    def _partition_alloc_details(self, renderer_dump):
        details = {
            'buffer': {},
            'fast_malloc': {},
        }
        allocators = renderer_dump['args']['dumps']['allocators']
        for fullname, dump in allocators.iteritems():
            parts = fullname.split('/')
            if parts[0] != 'partition_alloc_details':
                continue
            partition = parts[1]
            category = parts[2]
            if len(parts) <= 3 and category in ['vector', 'shared_buffer', 'hash_table', 'string_impl', 'others']:
                details[partition][category] = int(dump['attrs']['size']['value'], 16)
        return details

    def _partitions_sizes(self, renderer_dump):
        sizes = {}
        allocators = renderer_dump['args']['dumps']['allocators']
        for fullname, dump in allocators.iteritems():
            parts = fullname.split('/')
            if not fullname.startswith('partition_alloc/partitions') or len(parts) <= 2:
                continue
            if parts[-1] == 'allocated_objects': # Skip allocated objects.
                continue
            if not dump['attrs']['size']['units'] == 'bytes':
                continue
            category = parts[2]
            sizes[category] = sizes.get(category, 0) + int(dump['attrs']['size']['value'], 16)
        return sizes

    def _partitions_allocated_objects_sizes(self, renderer_dump):
        sizes = {}
        allocators = renderer_dump['args']['dumps']['allocators']
        for fullname, dump in allocators.iteritems():
            parts = fullname.split('/')
            if not fullname.startswith('partition_alloc/partitions'):
                continue
            if len(parts) != 3:
                continue
            category = parts[2]
            sizes[category] = sizes.get(category, 0) + int(dump['attrs']['allocated_objects_size']['value'], 16)
        return sizes


# TODO(bashi): We can't report 'malloc' because we use stl containers to
# hold live objects, which bloats memory usage of 'malloc' drastically.
_ALLOCATORS_TO_REPORT = [
    'partition_alloc', 'blink_gc', 'v8', 'skia', 'discardable', 'cc', 'malloc']

class TelemetoryResults(object):
    def __init__(self, results_json_path):
        with open(results_json_path) as f:
            self._results = json.load(f)
        self.pages = self._read_pages()

    def _read_html_traces(self, page_id):
        values = filter(lambda v: v['page_id'] == page_id and v['type'] == 'trace',
                        self._results['per_page_values'])
        assert(len(values) <= 1)
        if not values:
            return HTMLTrace() # An error occurred on this page.
        else:
            file_id = values[0]['file_id']
            path = self._results['files'][str(file_id)]
            return HTMLTrace(path)

    def _allocator_sizes(self, page_id):
        values = filter(lambda v: v['page_id'] == page_id,
                        self._results['per_page_values'])
        allocator_sizes = {}
        for allocator in _ALLOCATORS_TO_REPORT:
            name = 'memory_allocator_%s_renderer' % allocator
            sizes = [v['values'][0] for v in values
                     if v['name'] == name]
            assert(len(sizes) <= 1)
            if not sizes:
                allocator_sizes[allocator] = 0
            else:
                allocator_sizes[allocator] = sizes[0]
        return allocator_sizes

    def _read_pages(self):
        pages = {}
        for value in self._results['pages'].itervalues():
            page_id = value['id']
            html_trace = self._read_html_traces(page_id)
            allocator_sizes = self._allocator_sizes(page_id)
            name = value['name']
            pages[name] = {
                'allocator_sizes': allocator_sizes,
                'page_id': page_id,
                'partitions': html_trace.partitions,
                'partitions_allocated_sizes': html_trace.partitions_allocated_sizes,
                'partition_details': html_trace.partition_details,
                'name': name,
                'url': value['url'],
            }
        return pages


class SpreadSheetUpdater(object):
    def __init__(self, credential_path, sheet_id):
        self._credential_path = credential_path
        self._sheet_id = sheet_id
        self._prefix = time.strftime('%Y%m%d-%H%M%S')

    def upload(self, results):
        collection = hyou.login(self._credential_path)
        spreadsheet = collection[self._sheet_id]
        sorted_results = sorted(results.values(),
                                key=lambda page: page['page_id'])
        #self._upload_allocator_sizes(sorted_results, spreadsheet)
        #self._upload_partitions(sorted_results, spreadsheet)
        self._upload_partitions_allocated_sizes(sorted_results, spreadsheet)
        #self._upload_partition_buffer_details(sorted_results, spreadsheet)
        self._upload_partition_fast_malloc_details(sorted_results, spreadsheet)

    def _fill_page_names(self, results, worksheet):
        worksheet[0][0] = 'page'
        for i, page_values in enumerate(results):
            worksheet[i+1][0] = page_values.get('name', '<unknown>')

    def _fill_sizes(self, columns, getter_func, results, worksheet):
        for i, column_name in enumerate(columns):
            worksheet[0][i+1] = column_name
            for j, page_values in enumerate(results):
                size = getter_func(column_name, page_values)
                worksheet[j+1][i+1] = float(size) / 1024**2
        
    def _upload_allocator_sizes(self, results, spreadsheet):
        worksheet = spreadsheet.add_worksheet(
            '%s-allocators' % self._prefix,
            rows=len(results) + 1,
            cols=len(_ALLOCATORS_TO_REPORT) + 1)
        self._fill_page_names(results, worksheet)
        def size_getter(column_name, page_values):
            return page_values.get('allocator_sizes', {}).get(column_name, 0)
        self._fill_sizes(
            _ALLOCATORS_TO_REPORT, size_getter, results, worksheet)
        worksheet.commit()

    def _upload_partitions(self, results, spreadsheet):
        columns = sorted(results[0]['partitions'].keys())
        worksheet = spreadsheet.add_worksheet(
            '%s-partitions' % self._prefix,
            rows=len(results) + 1,
            cols=len(columns) + 1)
        self._fill_page_names(results, worksheet)
        def size_getter(column_name, page_values):
            return page_values.get('partitions', {}).get(column_name, 0)
        self._fill_sizes(columns, size_getter, results, worksheet)
        worksheet.commit()

    def _upload_partitions_allocated_sizes(self, results, spreadsheet):
        columns = sorted(results[0]['partitions_allocated_sizes'].keys())
        worksheet = spreadsheet.add_worksheet(
            '%s-partitions_allocated_sizes' % self._prefix,
            rows=len(results) + 1,
            cols=len(columns) + 1)
        self._fill_page_names(results, worksheet)
        def size_getter(column_name, page_values):
            return page_values.get('partitions_allocated_sizes', {}).get(column_name, 0)
        self._fill_sizes(columns, size_getter, results, worksheet)
        worksheet.commit()

    def _upload_partition_buffer_details(self, results, spreadsheet):
        columns = sorted(results[0]['partition_details']['buffer'].keys())
        worksheet = spreadsheet.add_worksheet(
            '%s-buffer_details' % self._prefix,
            rows=len(results) + 1,
            cols=len(columns) + 1)
        self._fill_page_names(results, worksheet)
        def size_getter(column_name, page_values):
            return page_values.get('partition_details', {}).get('buffer', {}).get(column_name, 0)
        self._fill_sizes(columns, size_getter, results, worksheet)
        worksheet.commit()

    def _upload_partition_fast_malloc_details(self, results, spreadsheet):
        columns = sorted(results[0]['partition_details']['fast_malloc'].keys())
        worksheet = spreadsheet.add_worksheet(
            '%s-fast_malloc_details' % self._prefix,
            rows=len(results) + 1,
            cols=len(columns) + 1)
        self._fill_page_names(results, worksheet)
        def size_getter(column_name, page_values):
            return page_values.get('partition_details', {}).get('fast_malloc', {}).get(column_name, 0)
        self._fill_sizes(columns, size_getter, results, worksheet)
        worksheet.commit()


def _parse_options():
    parser = OptionParser()
    parser.add_option('-c', '--credential', dest='credential',
                      help='path to credential.json')
    return parser.parse_args()


def report_as_dict(results_json_path):
    return TelemetoryResults(results_json_path).pages


def upload_to_spreadsheet(results_json_path, credential_path):
    results = TelemetoryResults(results_json_path).pages
    updater = SpreadSheetUpdater(
        credential_path,
        '1WZRpkrYG6KRbVWvey_3rf-LcHKAi7a444XaT0QqHfTw')
    updater.upload(results)


def main():
    opts, args = _parse_options()
    if opts.credential:
        upload_to_spreadsheet(args[0], opts.credential)
    else:
        results = report_as_dict(args[0])
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
