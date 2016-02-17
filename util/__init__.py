import os


_DEFAULT_CHROMIUM_PATH = os.path.abspath(
    os.path.join(os.environ['HOME'], 'chromium', 'src'))


def get_chromium_path():
    path = os.environ.get('CHROMIUM_SRC_DIR', _DEFAULT_CHROMIUM_PATH)
    if not os.path.exists(path):
        raise Exception('Set CHROMIUM_SRC_DIR environment variable')
    return path
