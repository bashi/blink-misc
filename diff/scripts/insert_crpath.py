import os
import sys

DEFAULT_CHROMIUM_PATH = os.path.abspath(
    os.path.join(os.environ['HOME'], 'chromium', 'src'))

_chromium_path = os.environ.get('CHROMIUM_SRC_DIR',
                                DEFAULT_CHROMIUM_PATH)
_blink_bindings_path = os.path.join(
    _chromium_path, 'third_party', 'WebKit', 'Source',
    'bindings', 'scripts')
sys.path.insert(0, _blink_bindings_path)
