import os

from util import insert_catapult_path
from util import get_chromium_path

from telemetry import benchmark_runner
from telemetry import project_config
from telemetry.internal import story_runner
from telemetry.internal.results import results_options
from telemetry.internal.util import command_line


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


# Partially copied from telemetry.telemetry.internal.story_runner.RunBenchmark
def run_benchmark(benchmark, finder_options):
    benchmark.CustomizeBrowserOptions(finder_options.browser_options)
    pt = benchmark.CreatePageTest(finder_options)
    pt.__name__ = benchmark.__class__.__name__
    stories = benchmark.CreateStorySet(finder_options)
    benchmark_metadata = benchmark.GetMetadata()
    with results_options.CreateResults(
            benchmark_metadata, finder_options,
            benchmark.ValueCanBeAddedPredicate) as results:
        failures = story_runner.Run(pt, stories, finder_options, results,
                                    benchmark.max_failures)
        results._SerializeTracesToDirPath(results._output_dir)
    return failures


class RecordTrace(benchmark_runner.Run):
    def Run(self, args):
        return run_benchmark(self._benchmark(), args)


def main():
    config = MyConfig()
    extra_commands = [RecordTrace]
    return benchmark_runner.main(config, extra_commands=extra_commands)


if __name__ == '__main__':
    main()
