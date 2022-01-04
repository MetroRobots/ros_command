import asyncio
import os
import re

from ros_command.terminal_display import DynamicLayoutTerminalDisplay, Gauge, HSplit, Log, Marquee, TerminalComponent
from ros_command.terminal_display import Text, VSplit

STATUS_COLORS = {
    'blocked': 'magenta',
    'queued': 'yellow',
    'active': 'blue',
    'finished': 'green',
    'failed': 'red',
    'skipped': 'cyan'
}

EMOJIS = {
    'melodic': '🎶',
    'noetic': '🤔',
    'eloquent': '🗣',
    'foxy': '🦊',
    'galactic': '🌌',
    'humble': '🤭',
    'rolling': '🎢',
}


class BuildStatusHeader(TerminalComponent):
    def __init__(self, status, display):
        self.status = status
        self.distro = os.environ.get('ROS_DISTRO', '')
        self.emoji = EMOJIS.get(self.distro, '')
        self.marquee = Marquee('rosbuild', display.get_colors(re.compile(r'[^_]*green')))

    def draw(self, display):
        marquee_s = str(self.marquee)
        elapsed_s = self.status.get_elapsed_time()
        if self.h == 1:
            display(self.emoji, xy=(self.x0, self.y0))
            display(marquee_s, xy=(self.x0 + 2, self.y0))
            display(display.white + elapsed_s, xy=(self.x0 + self.w - len(elapsed_s), self.y0))
        else:
            x1 = self.x0 + (self.w - self.marquee.n) // 2
            y1 = self.y0 + 1
            display(marquee_s, xy=(x1, y1))

            display(display.white + elapsed_s.center(self.w), xy=(self.x0, y1 + 1))

            if self.emoji:
                for dx in [0, 1]:
                    for dy in [0, 1]:
                        display(self.emoji, xy=(self.x0 + dx * (self.w - 2), self.y0 + dy * (self.h - 1)))

    def finish(self):
        self.marquee.finish()


class CombinedStatusDisplay(TerminalComponent):
    def __init__(self):
        self.active = []
        self.error = []

    def draw(self, display):
        self.clear(display)
        s = display.bright_blue + 'Active: ' + ', '.join(self.active)
        if self.error:
            s += '\n' + display.orangered + 'Failed: ' + ', '.join(self.error)
        display(s, (self.x0, self.y0))


class BuildStatusDisplay:
    def __init__(self, status, update_period=0.1):
        self.status = status
        self.term = DynamicLayoutTerminalDisplay()
        self.header = BuildStatusHeader(status, self.term)
        self.active_gui = Text(title='Active', border_color=self.term.bright_blue)
        self.error_gui = Text(title='Failed', border_color=self.term.orangered)
        self.complete_gui = Gauge(title='Complete', border_color=self.term.green)
        self.queued_gui = Gauge(title='Queued', border_color=self.term.goldenrod)
        self.blocked_gui = Gauge(title='Blocked', border_color=self.term.purple)
        self.log_gui = Log(title='Errors', border_color=self.term.firebrick)
        self.combined_gui = CombinedStatusDisplay()

        progress = HSplit(self.complete_gui, self.queued_gui, self.blocked_gui)
        self.term.large_layout = VSplit(
            HSplit(
                VSplit(self.header, self.active_gui, self.error_gui),
                self.log_gui
            ),
            progress,
            weights=[6, 1])
        self.term.small_layout = VSplit(
            self.header,
            self.combined_gui,
            progress,
            weights=[1, 60, 1])

        self.term.draw()

        self.update_period = 0.1
        self.task = asyncio.ensure_future(self.timer_cb())

    async def timer_cb(self):
        await asyncio.sleep(self.update_period)
        self.show()
        self.task = asyncio.ensure_future(self.timer_cb())

    def get_elapsed_time(self):
        return self.status.get_elapsed_time()

    def show(self):
        self.header.marquee.advance()
        self.active_gui.update(self.status.pkg_lists['active'])
        self.error_gui.update(self.status.pkg_lists['failed'])
        self.combined_gui.active = self.status.pkg_lists['active']
        self.combined_gui.error = self.status.pkg_lists['failed']
        self.complete_gui.update(len(self.status.pkg_lists['finished']), self.status.n)
        self.queued_gui.update(len(self.status.pkg_lists['queued']), self.status.n)
        self.blocked_gui.update(len(self.status.pkg_lists['blocked']), self.status.n)
        self.log_gui.update(self.status.error_buffer)
        self.term.draw()

    def finish(self):
        self.task.cancel()
        self.header.finish()
        self.term.finish()
        self.show()
