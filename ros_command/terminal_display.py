from math import ceil
import random

from blessed import Terminal
from blessed.formatters import COLORS, resolve_color


# Some elements borrowed from https://github.com/FedericoCeratto/dashing/blob/master/dashing/dashing.py
BOTTOM_LEFT = '└'
BOTTOM_RIGHT = '┘'
TOP_LEFT = '┌'
TOP_RIGHT = '┐'
HORIZONTAL = '─'
VERTICAL = '│'
HBAR_CHARS = [' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉']
LETTER_OFFSETS = [0x00061, 0x1D41A, 0x1D44E, 0x1D482, 0x1D5BA, 0x1D5EE, 0x1D622, 0x1D656,
                  0x1D4EA, 0x1D51E, 0x1D586, 0x1D68A, 0x1D552, 0x00041, 0x1D400, 0x1D434,
                  0x1D468, 0x1D5A0, 0x1D5D4, 0x1D608, 0x1D63C, 0x1D4D0, 0x1D56C, 0x1D670]
SPINNER = '🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛'


class TerminalDisplay:
    """Wrapper around blessed.Terminal that allows for easy xy printing."""

    def __init__(self):
        self.term = Terminal()
        print(self.home + self.clear)
        self.saved_size = None
        self.root = None

    def __call__(self, s, xy=None):
        """Mild hack to use the display object as a functor to call display('text', (5, 5))."""
        if xy:
            print(self.term.move_xy(*xy), end='')
        print(s, end='')

    def __getattr__(self, k):
        """Get colors and other properties from the terminal object."""
        return self.term.__getattr__(k)

    def draw(self):
        """Draw all the elements."""
        if self.root:
            size = (self.term.width, self.term.height - 1)
            if not self.saved_size or self.saved_size != size:
                print(self.clear)
                self.root.set_geometry((0, 0), size)
                self.saved_size = size
            self.root.draw(self)
        print(self.term.normal)

    def get_colors(self, pattern):
        """Get all the colors where the color name matches a given pattern."""
        for color_s in COLORS:
            m = pattern.match(color_s)
            if m:
                yield resolve_color(self.term, color_s)

    def finish(self):
        if self.root:
            self.root.finish()
        self.term.move_xy(0, self.term.height)


class DynamicLayoutTerminalDisplay(TerminalDisplay):
    def __init__(self):
        TerminalDisplay.__init__(self)
        self.small_layout = None
        self.large_layout = None
        self.cutoff = 12

    def draw(self):
        size = (self.term.width, self.term.height - 1)
        if self.root and self.saved_size and self.saved_size == size:
            self.root.draw(self)
            print(self.term.normal)
            return

        # Dynanmic Layout
        print(self.clear)
        if size[1] < self.cutoff:
            self.root = self.small_layout
        else:
            self.root = self.large_layout
        self.root.set_geometry((0, 0), size)
        self.root.draw(self)
        self.saved_size = size


class TerminalComponent:
    def __init__(self):
        self.set_geometry((0, 0), (0, 0))

    def set_geometry(self, xy, size):
        self.x0, self.y0 = xy
        self.w, self.h = size

    def draw(self, display):
        raise NotImplementedError()

    def clear(self, display):
        s = ' ' * self.w
        for dy in range(self.h):
            display(s, (self.x0, self.y0 + dy))

    def finish(self):
        pass


class Box(TerminalComponent):
    def __init__(self, title=None, border_color=None):
        TerminalComponent.__init__(self)
        self.base_title = title
        self.title = title
        self.border_color = border_color

    def draw(self, display):
        # top border
        s = TOP_LEFT + (HORIZONTAL * (self.w - 2)) + TOP_RIGHT
        if self.title:
            s = s[:2] + ' ' + self.title + ' ' + s[len(self.title) + 4:]
        display(self.border_color + s, xy=(self.x0, self.y0))

        # left and right
        for dy in range(1, self.h - 1):
            display(VERTICAL, xy=(self.x0, self.y0 + dy))
            display(VERTICAL, xy=(self.x0 + self.w - 1, self.y0 + dy))

        display(BOTTOM_LEFT + (HORIZONTAL * (self.w - 2)) + BOTTOM_RIGHT, xy=(self.x0, self.y0 + self.h - 1))


class Text(Box):
    def __init__(self, min_column_width=10, *args, **kwargs):
        Box.__init__(self, *args, **kwargs)
        self.min_column_width = min_column_width
        self.values = []

    def update(self, values):
        self.title = f'{self.base_title} {len(values)}'
        self.values = values

    def draw(self, display):
        Box.draw(self, display)

        columns = 1
        while len(self.values) // columns > self.h - 2 and (self.w - 2) // (columns + 1) > self.min_column_width:
            columns += 1

        index = 0
        cwidth = (self.w - 2) // columns
        for column in range(columns):
            for row in range(1, self.h - 1):
                if index < len(self.values):
                    s = self.values[index]
                    if len(s) > cwidth - 1:
                        s = s[:cwidth - 2] + '…'
                    index += 1
                else:
                    s = ''
                s += ' ' * (cwidth - len(s))
                display(s, xy=(self.x0 + 1 + cwidth * column, self.y0 + row))


class Log(Box):
    def __init__(self, text_color=None, *args, **kwargs):
        Box.__init__(self, *args, **kwargs)
        self.text_color = text_color
        self.lines = []

    def update(self, lines):
        max_lines = self.h - 2
        self.lines = []
        # Only save useful number of lines
        for line in lines[-max_lines:]:
            # Replace tabs with spaces for proper length computations
            fixed_line = line.replace('\t', '    ')
            self.lines.append(fixed_line)

    def draw(self, display):
        Box.draw(self, display)
        if self.text_color:
            display(self.text_color)
        for h in range(1, self.h - 1):
            if h - 1 < len(self.lines):
                s = self.lines[h - 1][:self.w - 2]
            else:
                s = ''
            s += ' ' * (self.w - 2 - len(s))
            display(s, xy=(self.x0 + 1, self.y0 + h))


class Gauge(Box):
    def __init__(self, *args, **kwargs):
        Box.__init__(self, *args, **kwargs)
        self.base_title = self.title
        self.level = 0.0

    def update(self, numerator, denominator):
        self.title = f'{self.base_title} {numerator}/{denominator}'
        if denominator:
            self.level = numerator / denominator

    def draw(self, display):
        if self.h >= 3:
            Box.draw(self, display)
            w = self.w - 2
            ys = range(1, self.h - 1)
            x1 = self.x0 + 1
        elif self.title:
            print(self.border_color)
            if self.h >= 1:
                w = self.w - len(self.title)
                x1 = self.x0 + len(self.title)
            else:
                w = self.w
                x1 = self.x0
            ys = range(self.h)
        else:
            print(self.border_color)
            w = self.w
            ys = range(self.h)
            x1 = self.x0

        filled = w * self.level
        i_filled = int(filled)
        s = i_filled * HBAR_CHARS[-1]
        remainder = filled - i_filled
        if len(s) < w:
            s += HBAR_CHARS[int(remainder * (len(HBAR_CHARS) - 1))]
            s += ' ' * (w - len(s))
        for dy in ys:
            display(s, xy=(x1, self.y0 + dy))
        if self.h < 3 and self.title:
            display(self.title, (self.x0, self.y0))


class StatusBoard(Box):
    def __init__(self, keys, status_colors, *args, **kwargs):
        Box.__init__(self, *args, **kwargs)
        self.keys = keys
        self.status_colors = status_colors
        self.statuses = {}
        self.spinner_index = 0

        self.column_width = 4 + max(len(s) for s in self.keys) if self.keys else 1

    def advance(self):
        self.spinner_index = (self.spinner_index + 1) % len(SPINNER)

    def draw(self, display):
        self.clear(display)
        Box.draw(self, display)

        row_index = list(range(self.y0 + 1, self.y0 + self.h - 1))
        num_rows = len(row_index)
        displayable_columns = ceil(self.w / self.column_width)
        skippable_columns = 0
        column_values = set()
        table = [[]]
        for key in self.keys:
            status = self.statuses.get(key)
            column_values.add(status)
            status_color, status_char = self.get_status_formatting(status)
            table[-1].append(f'{status_color}{status_char} {key}')
            if len(table[-1]) >= num_rows:
                if None not in column_values and 'active' not in column_values:
                    skippable_columns += 1
                column_values = set()
                table.append([])

        start_column_index = max(skippable_columns - displayable_columns + 2, 0)
        for col_i, column in enumerate(table[start_column_index:]):
            for row_i, s in enumerate(column):
                x = self.x0 + col_i * self.column_width + 2
                if x + self.column_width > self.w:
                    break
                display(s, xy=(x, row_index[row_i]))

    def get_status_formatting(self, status):
        color = self.status_colors.get(status, self.status_colors[None])

        if status == 'failure':
            status_char = '❌'
        elif status == 'success':
            status_char = '✅'
        elif status == 'active':
            status_char = SPINNER[self.spinner_index]
        else:
            status_char = '🔲'
        return color, status_char


class Splitter(TerminalComponent):
    def __init__(self, *elements, weights=None):
        self.elements = elements
        self.weights = weights

    def get_sizes(self, total_size):
        N = len(self.elements)
        if N > total_size:
            return [1] * total_size + [0] * (N - total_size)
        if self.weights is None:
            ratios = [1 / N] * N
        else:
            denominator = sum(self.weights)
            ratios = [weight / denominator for weight in self.weights]

        factor = 1.0
        sizes = [max(1, int(ratio * total_size * factor)) for ratio in ratios]
        while sum(sizes) >= total_size:
            factor *= 0.95
            sizes = [max(1, int(ratio * total_size * factor)) for ratio in ratios]

        # If leftover, add to last section
        remainder = total_size - sum(sizes)
        if remainder:
            sizes[-1] += remainder
        return sizes

    def draw(self, display):
        for element in self.elements:
            element.draw(display)

    def finish(self):
        for element in self.elements:
            element.finish()


class HSplit(Splitter):
    def set_geometry(self, xy, size):
        x0, y0 = xy
        w, h = size

        for element, w1 in zip(self.elements, self.get_sizes(w)):
            element.set_geometry((x0, y0), (w1, h))
            x0 += w1


class VSplit(Splitter):
    def set_geometry(self, xy, size):
        x0, y0 = xy
        w, h = size

        for element, h1 in zip(self.elements, self.get_sizes(h)):
            element.set_geometry((x0, y0), (w, h1))
            y0 += h1


class Marquee:
    def __init__(self, text, colors):
        self.char_codes = [ord(c) - ord('a') for c in text.lower()]
        self.colors = list(colors)
        self.n = len(text)
        self.index = 0
        self.start_offset, self.start_color = self.get_random_offset_and_color()
        self.end_offset, self.end_color = self.get_random_offset_and_color()

    def get_random_offset_and_color(self):
        return random.choice(LETTER_OFFSETS), random.choice(self.colors)

    def advance(self):
        self.index += 1
        if self.index <= self.n:
            return

        # Reset
        self.end_offset = self.start_offset
        self.end_color = self.start_color
        self.start_offset, self.start_color = self.get_random_offset_and_color()
        self.index = 0

    def finish(self):
        self.index = self.n

    def __repr__(self):
        s = self.start_color
        for i, cc in enumerate(self.char_codes):
            if i == self.index:
                s += self.end_color

            if i < self.index:
                offset = self.start_offset
            else:
                offset = self.end_offset

            s += chr(cc + offset)
        return s
