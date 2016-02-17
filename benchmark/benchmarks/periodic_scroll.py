from benchmark.page_sets import scroll
from benchmark.benchmarks import memory_infra


class PeriodicScrollDesktop(memory_infra._MemoryInfraBenchmark):
    page_set = scroll.BlinkDesktopPageSet

    @classmethod
    def Name(cls):
        return 'periodic_scroll.desktop'


class PeriodicScrollMobile(memory_infra._MemoryInfraBenchmark):
    page_set = scroll.BlinkMobilePageSet

    @classmethod
    def Name(cls):
        return 'periodic_scroll.mobile'

    def CreateTimelineBasedMeasurementOptions(self):
        tbm_options = super(
            PeriodicScrollMobile,
            self).CreateTimelineBasedMeasurementOptions()
        tbm_options.config.enable_android_graphics_memtrack = True
        return tbm_options
