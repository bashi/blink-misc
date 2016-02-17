import json
import math
import os
import sys


def calc_stats(values):
    total = 0.0
    doubled = 0.0
    hiest = values[0]
    lowest = values[0]
    for value in values:
        total += value
        doubled += value * value
        if lowest > value:
            lowest = value
        if hiest < value:
            hiest = value
    average = total / len(values)
    variance = doubled / len(values) - average * average
    return {
        'average': average,
        'variance': variance,
        'hiest': hiest,
        'lowest': lowest,
    }


# This should be synced with mappers/peak_resident_sizes_map_function.html
_PEAK_VALUE_NAME = 'peakResidentBytes'

class Peaks(object):
    def __init__(self):
        # label -> peaks
        self._pages = {}

    def add_mapping_result(self, results):
        peak_values = [v for v in results['values']
                       if v.get('name') == _PEAK_VALUE_NAME]
        for value in peak_values:
            for peak in value['value'].itervalues():
                label = peak['label']
                if not label in self._pages.keys():
                    self._pages[label] = []
                self._pages[label].append(peak['size'])

    def get_stats(self):
        return {label: calc_stats(values) for label, values
                in self._pages.iteritems()}


def main(args):
    peaks = Peaks()
    for path in args:
        with open(path) as f:
            obj = json.load(f)
        peaks.add_mapping_result(obj)
    stats = peaks.get_stats()
    for label in sorted(stats):
        stat = stats[label]
        print('[%s]\n%.2f, %.2f, %.2f, %.2f' % (
            label.encode('utf-8'),
            stat['average'] / 1024**2,
            float(stat['lowest']) / 1024**2,
            float(stat['hiest']) / 1024**2,
            math.sqrt(stat['variance']) / 1024**2))


if __name__ == '__main__':
    main(sys.argv[1:])
