import os

from util import insert_catapult_path
from util import get_chromium_path

from telemetry import benchmark_runner
from telemetry import project_config


_CHROMIUM_CLIENT_CONFIG_PATH = os.path.join(
    get_chromium_path(), 'tools', 'perf', 'chrome_telemetry_build',
    'binary_dependencies.json')
_BENCHMARK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'benchmarks')


class MyConfig(project_config.ProjectConfig):
    def __init__(self, top_level_dir=None, benchmark_dirs=None,
                 client_config=_CHROMIUM_CLIENT_CONFIG_PATH,
                 default_chrome_root=get_chromium_path()):
        if not top_level_dir:
            current_path = os.path.join(os.path.dirname(__file__), '..')
            top_level_dir = os.path.abspath(current_path)
        if not benchmark_dirs:
            benchmark_dirs = [_BENCHMARK_DIR]
        super(MyConfig, self).__init__(
            top_level_dir=top_level_dir, benchmark_dirs=benchmark_dirs,
            client_config=client_config,
            default_chrome_root=default_chrome_root)


def main():
    config = MyConfig()
    return benchmark_runner.main(config)
