import logging
import re

from telemetry import benchmark
from telemetry.timeline import tracing_category_filter
from telemetry.web_perf import timeline_based_measurement
from telemetry.web_perf.metrics import memory_timeline

from telemetry.page import page as page_module
from telemetry.page import shared_page_state
from telemetry import story


class ScrollDesktopPage(page_module.Page):
    def __init__(self, url, page_set, name):
        super(ScrollDesktopPage, self).__init__(
            url=url, page_set=page_set, name=name,
            shared_page_state_class=shared_page_state.SharedDesktopPageState,
            credentials_path='data/credentials.json')
        self.archive_data_file = 'data/scroll_desktop_page.json'

    def _DumpMemory(self, action_runner, phase):
        with action_runner.CreateInteraction(phase):
            if not action_runner.tab.browser.DumpMemory():
                logging.error('Unable to get memory dump for %s' % self.name)

    def RunPageInteractions(self, action_runner):
        action_runner.ScrollPage()
        self._DumpMemory(action_runner, 'scrolled')


class BlinkDesktopPageSet(story.StorySet):
    def __init__(self):
        super(BlinkDesktopPageSet, self).__init__(
            archive_data_file='data/blink_memory_desktop.json',
            cloud_storage_bucket=story.PARTNER_BUCKET)

        self.AddStory(ScrollDesktopPage(
            url='http://en.m.wikipedia.org/wiki/Wikipedia',
            page_set=self,
            name='Wikipedia'))


class ScrollMobilePage(page_module.Page):
    def __init__(self, url, page_set, name):
        super(ScrollMobilePage, self).__init__(
            url=url, page_set=page_set, name=name,
            shared_page_state_class=shared_page_state.SharedMobilePageState,
            credentials_path='data/credentials.json')
        self.archive_data_file = 'data/scroll_mobile_page.json'

    def _DumpMemory(self, action_runner, phase):
        with action_runner.CreateInteraction(phase):
            if not action_runner.tab.browser.DumpMemory():
                logging.error('Unable to get memory dump for %s' % self.name)

    def RunPageInteractions(self, action_runner):
        action_runner.ScrollPage()
        self._DumpMemory(action_runner, 'scrolled')


class BlinkMobilePageSet(story.StorySet):
    def __init__(self):
        super(BlinkMobilePageSet, self).__init__(
            archive_data_file='data/blink_memory_mobile.json',
            cloud_storage_bucket=story.PARTNER_BUCKET)

        self.AddStory(ScrollMobilePage(
            url='http://en.m.wikipedia.org/wiki/Wikipedia',
            page_set=self,
            name='Wikipedia'))

    def _DumpMemory(self, action_runner, phase):
        with action_runner.CreateInteraction(phase):
            if not action_runner.tab.browser.DumpMemory():
                logging.error('Unable to get memory dump for %s' % self.name)

    def RunPageInteractions(self, action_runner):
        action_runner.ScrollPage()
        self._DumpMemory(action_runner, 'scrolled')


class MemoryTimelineBlinkDesktop(benchmark.Benchmark):
    page_set = BlinkDesktopPageSet

    def SetExtraBrowserOptions(self, options):
        options.AppendExtraBrowserArgs([
            '--enable-memory-benchmarking',
        ])

    def CreateTimelineBasedMeasurementOptions(self):
        trace_memory = tracing_category_filter.TracingCategoryFilter(
            filter_string='-*,blink.console,disabled-by-default-memory-infra')
        tbm_options = timeline_based_measurement.Options(
            overhead_level=trace_memory)
        return tbm_options

    @classmethod
    def Name(cls):
        return 'memory_timeline.blink_desktop'

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

class MemoryTimelineBlinkMobile(benchmark.Benchmark):
    page_set = BlinkMobilePageSet

    def SetExtraBrowserOptions(self, options):
        options.AppendExtraBrowserArgs([
            '--enable-memory-benchmarking',
        ])

    def CreateTimelineBasedMeasurementOptions(self):
        trace_memory = tracing_category_filter.TracingCategoryFilter(
            filter_string='-*,blink.console,disabled-by-default-memory-infra')
        tbm_options = timeline_based_measurement.Options(
            overhead_level=trace_memory)
        return tbm_options

    @classmethod
    def Name(cls):
        return 'memory_timeline.blink_mobile'

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
