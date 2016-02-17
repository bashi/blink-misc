import logging
import re

from telemetry.page import page as page_module
from telemetry.page import shared_page_state
from telemetry import story


class ScrollPageBase(page_module.Page):
    def __init__(self, url, page_set, name, shared_page_state_class):
        super(ScrollPageBase, self).__init__(
            url=url, page_set=page_set, name=name,
            shared_page_state_class=shared_page_state_class,
            credentials_path='data/credentials.json')
        self.archive_data_file = 'data/scroll_desktop_page.json'

    def _DumpMemory(self, action_runner, phase):
        with action_runner.CreateInteraction(phase):
            if not action_runner.tab.browser.DumpMemory():
                logging.error('Unable to get memory dump for %s' % self.name)

    def RunPageInteractions(self, action_runner):
        action_runner.ScrollPage()
        self._DumpMemory(action_runner, 'scrolled')


class ScrollPageSetBase(story.StorySet):
    def __init__(self, archive_data_file,
                 page_set_class, shared_page_state_class):
        super(ScrollPageSetBase, self).__init__(
            archive_data_file=archive_data_file,
            cloud_storage_bucket=story.PARTNER_BUCKET)

        urls = [
            ('http://www.theverge.com', 'TheVerge'),
            # ('http://mobile.nytimes.com/', 'NewYorkTimes'),
            # ('http://www.reddit.com/r/programming/comments/1g96ve', 'Reddit'),
            # ('http://en.m.wikipedia.org/wiki/Wikipedia', 'Wikipedia'),
        ]

        for url in urls:
            self.AddStory(page_set_class(
                url=url[0],
                page_set=self,
                name=url[1]))


# Desktop

class ScrollDesktopPage(ScrollPageBase):
    def __init__(self, url, page_set, name):
        super(ScrollDesktopPage, self).__init__(
            url=url, page_set=page_set, name=name,
            shared_page_state_class=shared_page_state.SharedDesktopPageState)
        self.archive_data_file = 'data/scroll_desktop_page.json'


class BlinkDesktopPageSet(ScrollPageSetBase):
    def __init__(self):
        super(BlinkDesktopPageSet, self).__init__(
            archive_data_file='data/blink_memory_desktop.json',
            page_set_class=ScrollDesktopPage,
            shared_page_state_class=shared_page_state.SharedDesktopPageState)


# Mobile

class ScrollMobilePage(ScrollPageBase):
    def __init__(self, url, page_set, name):
        super(ScrollMobilePage, self).__init__(
            url=url, page_set=page_set, name=name,
            shared_page_state_class=shared_page_state.SharedMobilePageState)
        self.archive_data_file = 'data/scroll_mobile_page.json'


class BlinkMobilePageSet(ScrollPageSetBase):
    def __init__(self):
        super(BlinkMobilePageSet, self).__init__(
            archive_data_file='data/blink_memory_mobile.json',
            page_set_class=ScrollMobilePage,
            shared_page_state_class=shared_page_state.SharedMobilePageState)
