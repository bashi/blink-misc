#!/usr/bin/env python

import argparse
import os
import re
import sys
import time

from util import insert_catapult_path

from devil.android import device_utils
from devil.android.logcat_monitor import LogcatMonitor
from devil.android.sdk.adb_wrapper import AdbWrapper
from devil.android.sdk.intent import Intent


_TRACING_CATEGORIES = ','.join([
    '-*',
    'blink',
    'blink_style',
    'blink.net',
    'cc',
    'gpu',
    'loader',
    'renderer',
    'skia',
    'v8',
    'WebCore',
    'disabled-by-default-memory-infra',
])

_TRACE_FILE = os.path.join('/', 'sdcard', 'Download', 'trace.json')
_COMMAND_LINE_FILE = os.path.join('/', 'data', 'local', 'chrome-command-line')
_TRACING_END_REGEXP = re.compile(r' Completed startup tracing to (.*)')


class Runner(object):
    def __init__(self, duration, serial=None):
        if not AdbWrapper.IsServerOnline():
            AdbWrapper.StartServer()
        if serial:
            devices = [device_utils.DeviceUtils(serial, default_retries=0)]
        else:
            devices = device_utils.DeviceUtils.HealthyDevices(default_retries=0)
        if not devices:
            raise ValueError('Cannot find device')
        self._adb = devices[0]
        self._logcat = self._adb.GetLogcatMonitor()
        self._duration = duration

    def _config_command_line(self):
        lines = ' '.join(["chrome",
                 "--trace-startup='" + _TRACING_CATEGORIES + "'",
                 "--trace-startup-file=" + _TRACE_FILE,
                 "--trace-startup-duration=%d" % self._duration,
                 "--enable-heap-profiling",
                 "--no-sandbox",
        ])
        self._adb.WriteFile(_COMMAND_LINE_FILE, lines, as_root=True)
        self._adb.RunShellCommand(['chmod', '0664', _COMMAND_LINE_FILE],
                                  as_root=True)

    def _open(self, url):
        intent = Intent(action='android.intent.action.VIEW',
                        package='org.chromium.chrome',
                        activity='com.google.android.apps.chrome.Main',
                        data=url)
        self._adb.StartActivity(intent)

    def _force_stop(self):
        try:
            self._adb.KillAll('chrome')
        except:
            pass

    def _wait_for_tracing(self):
        timeout = self._duration + 10
        result = self._logcat.WaitFor(_TRACING_END_REGEXP, timeout=timeout)
        return result.group(1)

    def _pull_trace(self, trace_file):
        time.sleep(3)
        host_file = os.path.join(os.path.curdir, os.path.basename(trace_file))
        self._adb.PullFile(trace_file, host_file)
        return host_file

    def start(self, url):
        self._force_stop()
        self._config_command_line()
        time.sleep(2)
        self._logcat.Start()
        self._open(url)
        trace_file = self._wait_for_tracing()
        return self._pull_trace(trace_file)


def get_trace_for(url, duration=10):
    r = Runner(duration)
    trace_file = r.start(url)
    print('Done: ' + os.path.abspath(trace_file))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--duration', dest='duration',
                        type=int, default=10,
                        help='Time to trace allocation.')
    return parser.parse_known_args()


def main(args):
    opts, args = parse_args()
    if len(args) != 1:
        raise ValueError('Must specify a URL')
    get_trace_for(args[0], opts.duration)


if __name__ == '__main__':
    main(sys.argv[1:])
