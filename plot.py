#!/usr/bin/env python3

"""Plot gamma curves"""

import turtle

class Plot:
    """Class to plot gamma gamma curves and keep track of zoom level"""
    def __init__(self, vlines=()):
        self.plot_area = (-1, -1, 256, 1024)
        self.min_size = (4, 16)
        self.zoom_area = [*self.plot_area]
        self.zoom()
        self.draw_grid(vlines=vlines)

    def clear(self, vlines=()):
        """Clear plot and draw grid lines"""
        turtle.clear()
        self.draw_grid(vlines=vlines)

    def zoom(self, level=None, direction=(0, 0)):
        """Zoom in or out"""
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

        turtle.setworldcoordinates(*self.zoom_area)

    def draw_grid(self, vlines=()):
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
        for vline in vlines:
            if vline is not None:
                turtle.setposition(vline, 1)
                turtle.pendown()
                turtle.setposition(vline, 1023)
                turtle.penup()
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
    p.clear(vlines=[i for i in range(16, 256-15, 16)])
    p.plot([512 for i in range(256)], draw_speed=4)
    p.clear()
    p.plot([512 for i in range(256)], draw_speed=4)
    p.clear(vlines=range(256))
    p.plot([512 for i in range(256)], draw_speed=2)
    p.clear(vlines=[127, 128])
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
