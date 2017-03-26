#!/usr/bin/env python3

"""Plot gamma curves"""

import math
import numbers
import turtle
from tkinter.font import Font

class Plot:
    """Class to plot gamma gamma curves and keep track of zoom level"""
    def __init__(self, lines=()):
        self.margin = [0, 0, 0, 0]
        self.plot_area = (0, 0, 255, 1023)
        self.min_size = (2, 8)
        self.zoom_area = [*self.plot_area]
        self.font = ('Ariel', 8)
        self.zoom()
        self.draw_grid(lines=lines)

    def clear(self, lines=()):
        """Clear plot and draw grid lines"""
        turtle.clear()
        self.draw_grid(lines=lines)

    def setworldcoordinates(self):
        """Update window after zoom or margin change"""
        turtle.setworldcoordinates(*(a + b * self.scale
                                     for a, b in zip(self.zoom_area, self.margin)))

    def zoom(self, level=None, direction=(0, 0)):
        """Zoom in or out"""
        self.scale = 1
        if level is None:
            self.zoom_area = [*self.plot_area]
        else:
            for i in range(2):
                l = self.zoom_area[i]
                h = self.zoom_area[i + 2]
                d = direction[i]/2 + 0.5
                min_l = self.plot_area[i]
                max_h = self.plot_area[i + 2]
                max_size = max_h - min_l
                size = h - l
                new_size = size / level
                if new_size < self.min_size[i]:
                    new_size = self.min_size[i]
                if new_size > max_size:
                    new_size = max_size
                new_l = max(min_l, l + (size - new_size) * d)
                new_h = new_l + new_size
                if new_h > max_h:
                    new_h = max_h
                    new_l = new_h - new_size
                self.zoom_area[i], self.zoom_area[i + 2] = new_l, new_h
                self.scale = new_size / max_size

        self.setworldcoordinates()

    def label_size(self, label):
        """Calculate label size"""
        font_family, font_size = self.font
        font = Font(family=font_family, size=font_size)
        width = 0
        lines = 0
        for line in label.split('\n'):
            width = max(width, font.measure(line))
            lines += 1
        xscale = turtle.getscreen().xscale
        yscale = turtle.getscreen().yscale
        return width / xscale, font.metrics('linespace') * lines / yscale

    def label_pos(self, pos, label=None, horizontal=False):
        """Calculate label start position (top-right if vertical, top-center if horizontal)"""
        xscale = turtle.getscreen().xscale
        yscale = turtle.getscreen().yscale
        font_family, font_size = self.font
        font = Font(family=font_family, size=font_size)
        line_height = font.metrics('linespace') / yscale
        height = (label.count('\n') + 1) * line_height
        return -8 / xscale if horizontal else pos, \
               pos - 0.5 * height if horizontal else -height - 6 / yscale

    def draw_line(self, pos, horizontal=False, label=None,
                  color='gray90', label_color='gray35', **_):
        """Draw one horizontal or vertical line with optional color and label"""
        if pos is None:
            return
        if pos < self.zoom_area[0 + horizontal] or pos > self.zoom_area[2 + horizontal]:
            return
        turtle.penup()
        xscale = turtle.getscreen().xscale
        yscale = turtle.getscreen().yscale
        if label:
            font_family, font_size = self.font
            turtle.color(label_color)
            turtle.setposition(*self.label_pos(pos=pos, label=label, horizontal=horizontal))
            turtle.write(label, align='right' if horizontal else'center',
                         font=(font_family, font_size))
            turtle.setposition(-4 / xscale if horizontal else pos,
                               pos if horizontal else -4 / yscale)
            turtle.pendown()
        turtle.setposition(1 / xscale if horizontal else pos,
                           pos if horizontal else 1 / yscale)
        turtle.color(color)
        turtle.pendown()
        turtle.setposition(self.plot_area[2] if horizontal else pos,
                           pos if horizontal else self.plot_area[3])
        turtle.penup()

    def draw_grid(self, lines=()):
        """Draw grid lines"""
        turtle.tracer(0)
        turtle.hideturtle()
        turtle.speed(0)
        turtle.penup()
        turtle.color('gray75')
        turtle.setposition(0, 0)
        turtle.pendown()
        turtle.setposition(255, 0)
        turtle.setposition(255, 1023)
        turtle.setposition(0, 1023)
        turtle.setposition(0, 0)
        turtle.penup()
        turtle.color('gray90')

        lines = [line.copy() for line in lines]
        lines.sort(key=lambda x: x['pos'])
        last = [None, None]
        last_pos = [-math.inf, -math.inf]

        margin_pad = 4 / turtle.getscreen().xscale, 4 / turtle.getscreen().yscale
        margin_scale = 1 / self.scale, 1 / self.scale
        margin = [sign * pad * scale
                  for sign in (-1, 1)
                  for pad, scale in zip(margin_pad, margin_scale)]

        for i, line in enumerate(lines):
            label = line.get('label')
            if not label:
                continue
            h = line.get('horizontal', 0)
            pos = line['pos']
            if pos < self.zoom_area[0 + h] or pos > self.zoom_area[2 + h]:
                del line['label']
                continue
            size = self.label_size(label)
            label_pos = self.label_pos(pos=pos, label=label, horizontal=h)
            label_pos = (label_pos[0] - size[0] / (1 if h else 2), label_pos[1])

            for i, p in enumerate(label_pos):
                pl = (p - margin_pad[i]) * margin_scale[i]
                if pl < margin[i]:
                    margin[i] = pl
                ph = (p + size[i] - self.plot_area[i + 2] + margin_pad[i]) * margin_scale[i]
                if ph > margin[i + 2]:
                    margin[i + 2] = ph

        resize = False
        for i, p in enumerate(margin):
            if p != self.margin[i] and i < 2:
                self.margin[i] = p
                resize = True
            if p != self.margin[i] and i >= 2:
                self.margin[i] = p
                resize = True
        if resize:
            self.setworldcoordinates()

        for i, line in enumerate(lines):
            label = line.get('label')
            if not label:
                continue
            h = line.get('horizontal', 0)
            pos = line['pos']
            size = self.label_size(label)
            pad = size[h] * 0.6

            if pos - pad < last_pos[h]:
                if line.get('priority', 0) <= last[h].get('priority', 0):
                    del line['label']
                    continue
                del last[h]['label']
            last[h] = line
            last_pos[h] = pos + pad

        for line in lines:
            if line is not None:
                if isinstance(line, numbers.Number):
                    line = (line,)
                self.draw_line(**line)
        turtle.update()

    def plot(self, *gamma, colors=['red', 'green', 'blue'], draw_speed=16, scale_x=1):
        """Plot gamma table"""

        if len(gamma) == 1 and len(gamma[0]) == 3:
            gamma = gamma[0]
        if all(x == gamma[0] for x in gamma):
            gamma = gamma[:1]

        turtle.penup()
        turtle.tracer(0, 16)
        turtle.speed(0)
        turtle.color('black')
        for color, points_y in enumerate(gamma):
            if len(gamma) == len(colors):
                turtle.color(colors[color])
            elif len(colors) == 1:
                turtle.color(colors[0])
            for x, y in enumerate(points_y):
                trace = x and x % draw_speed == 0
                if trace:
                    turtle.tracer(1)
                turtle.setposition(x * scale_x, y)
                if trace:
                    turtle.tracer(0)
                if x == 0:
                    turtle.showturtle()
                    turtle.pendown()

            turtle.penup()
            turtle.hideturtle()
            turtle.update()

def main():
    """Test Plot class"""
    p = Plot()
    p.plot([512 for i in range(256)], draw_speed=4)
    p.clear(lines=
            [{'pos': i, 'label': str(i)} for i in list(range(16, 256-15, 16)) + [255]] +
            [{'pos': i, 'horizontal': True, 'label': str(i)}
             for i in range(64, 1024-63, 64)])
    p.plot([512 for i in range(256)], draw_speed=4)
    p.clear(lines=[{'pos': 128, 'label': 'Green line\nlabel', 'color': 'green'},
                   {'pos': 136, 'label': 'Blue\nline\nlabel', 'priority': 1,
                    'color': 'blue'}])
    p.plot([512 for i in range(256)], draw_speed=4)
    p.zoom(4, (0, -1))
    p.clear(lines=[{'pos': 128, 'label': 'Green line\nlabel', 'color': 'green'},
                   {'pos': 136, 'label': 'Blue\nline\nlabel', 'color': 'blue'}])
    p.plot([512 for i in range(256)], draw_speed=4)
    p.clear()
    p.zoom()
    p.plot([512 for i in range(256)], draw_speed=4)
    p.clear(lines=[{'pos': i} for i in range(256)])
    p.plot([512 for i in range(256)], draw_speed=2)
    p.clear(lines=[{'pos': 127}, {'pos':128}])
    p.plot([i << 2 | i >> 6 for i in range(256)])
    p.plot([i << 2 | i >> 6 for i in range(255, -1, -1)], colors=['red'])
    p.zoom(4, (0, 0))
    p.plot([i << 2 | i >> 6 for i in range(256)], draw_speed=2, colors=['green'])
    p.zoom(2, (-1, 0))
    p.plot([i << 2 | i >> 6 for i in range(256)], draw_speed=2, colors=['green'])
    p.zoom()
    turtle.setpos(100, 512)
    turtle.write('test done')
    turtle.update()
    turtle.exitonclick()

if __name__ == "__main__":
    main()
