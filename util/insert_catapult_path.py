import os
import sys

from util import get_chromium_path

_chromium_path = get_chromium_path()
_catapult_path = os.path.join(_chromium_path, 'third_party', 'catapult')

sys.path.insert(0, os.path.join(_catapult_path, 'devil'))
sys.path.insert(0, os.path.join(_catapult_path, 'perf_insights'))
sys.path.insert(0, os.path.join(_catapult_path, 'telemetry'))
sys.path.insert(0, os.path.join(_catapult_path, 'tracing'))
