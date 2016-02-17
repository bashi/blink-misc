import json
import os
import sys


def get_name(peak_obj):
    index = peak_obj['name'].find(': ')
    if index < 0:
        return None
    return peak_obj['name'][index+2:]


class Average(object):
    def __init__(self):
        # page name -> peaks
        self._pages = {}

    def add_mapping_result(self, results):
        for value in results['values']:
            for peak in value['value'].itervalues():
                name = get_name(peak)
                if not name:
                    continue
                if not name in self._pages.keys():
                    self._pages[name] = []
                self._pages[name].append(peak['size'])

    def print_calc(self):
        for page_name in sorted(self._pages):
            peaks = self._pages[page_name]
            total = 0.0
            lowest = peaks[0]
            hiest = peaks[0]
            for size in peaks:
                total += size
                if lowest > size:
                    lowest = size
                if hiest < size:
                    hiest = size
            average = total / len(peaks)
            print('[%s]\n  %.2f, %.2f, %.2f' % (
                page_name,
                average / 1024**2,
                float(lowest) / 1024**2,
                float(hiest) / 1024**2))
            #print('%.2f' % (float(lowest) / 1024**2))


def main(args):
    average = Average()
    for path in args:
        with open(path) as f:
            obj = json.load(f)
        average.add_mapping_result(obj)
    average.print_calc()


if __name__ == '__main__':
    main(sys.argv[1:])
