from benchmark.page_sets import scroll
from benchmark.benchmarks import memory_infra


class _TimelineBasedMemoryBenchmark(memory_infra._MemoryInfraBenchmark):
    def SetExtraBrowserOptions(self, options):
        options.AppendExtraBrowserArgs([
            '--enable-heap-profiling',
            '--enable-memory-benchmarking',
        ])

    
class TimelineBasedScrollDesktop(_TimelineBasedMemoryBenchmark):
    page_set = scroll.BlinkDesktopPageSet

    @classmethod
    def Name(cls):
        return 'tbm_scroll.desktop'


class TimelineBasedScrollMobile(_TimelineBasedMemoryBenchmark):
    page_set = scroll.BlinkMobilePageSet

    @classmethod
    def Name(cls):
        return 'tbm_scroll.mobile'

    def CreateTimelineBasedMeasurementOptions(self):
        tbm_options = super(
            TimelineBasedScrollMobile,
            self).CreateTimelineBasedMeasurementOptions()
        tbm_options.config.enable_android_graphics_memtrack = True
        return tbm_options
