import re

from telemetry import benchmark
from telemetry.timeline import tracing_category_filter
from telemetry.web_perf import timeline_based_measurement
from telemetry.web_perf.metrics import memory_timeline


class _MemoryInfraBenchmark(benchmark.Benchmark):
    def CustomizeBrowserOptions(self, options):
        super(_MemoryInfraBenchmark, self).CustomizeBrowserOptions(
            options)
        self.SetExtraBrowserOptions(options)

    def SetExtraBrowserOptions(self, options):
        options.AppendExtraBrowserArgs([
            '--enable-heap-profiling',
        ])

    def CreateTimelineBasedMeasurementOptions(self):
        trace_memory = tracing_category_filter.TracingCategoryFilter(
            filter_string='-*,blink.console,disabled-by-default-memory-infra')
        tbm_options = timeline_based_measurement.Options(
            overhead_level=trace_memory)
        return tbm_options

    _RE_RENDERER_VALUES = re.compile('memory_.+_renderer')

    @classmethod
    def ValueCanBeAddedPredicate(cls, value, is_first_result):
        return bool(cls._RE_RENDERER_VALUES.match(value.name))

    @classmethod
    def HasBenchmarkTraceRerunDebugOption(cls):
        return True

    def SetupBenchmarkDefaultTraceRerunOptions(self, tbm_options):
        tbm_options.SetLegacyTimelineBasedMetrics((
            memory_timeline.MemoryTimelineMetric(),
        ))
