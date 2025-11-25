import fileinput
import math
import argparse
import os
import platform
import subprocess
import sys
import tempfile
from functools import cache


class Dimension:
    def __init__(self, xyz):
        (x, y, z) = map(int, xyz.split("x"))
        self.x = x
        self.y = y
        self.z = z

    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z
        else:
            raise IndexError("Dimension index out of range")


class Rgb:
    def __init__(self, r, g, b, a=1.0):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def lighten(self, factor):
        return Cmyk.from_rgb(self).lighten(factor).to_rgba()

    def darken(self, factor):
        return Cmyk.from_rgb(self).darken(factor).to_rgba()

    def __getitem__(self, item):
        if item == 0:
            return self.r
        elif item == 1:
            return self.g
        elif item == 2:
            return self.b
        elif item == 3:
            return self.a
        else:
            raise IndexError("Rgb index out of range")

    def __str__(self):
        def fmt(channel):
            return int(channel * 255)

        return f"Rgb({fmt(self.r)}, {fmt(self.g)}, {fmt(self.b)}, {fmt(self.a)})"


class Cmyk:
    def __init__(self, c, m, y, k):
        self.c = c
        self.m = m
        self.y = y
        self.k = k

    @staticmethod
    def from_rgb(rgb):
        (r, g, b, _) = rgb

        k = 1.0 - max(r, g, b)
        if k == 1.0:
            return Cmyk(0, 0, 0, 1)

        c = (1.0 - r - k) / (1.0 - k)
        m = (1.0 - g - k) / (1.0 - k)
        y = (1.0 - b - k) / (1.0 - k)

        return Cmyk(c, m, y, k)

    def to_rgba(self):
        r = (1.0 - self.c) * (1.0 - self.k)
        g = (1.0 - self.m) * (1.0 - self.k)
        b = (1.0 - self.y) * (1.0 - self.k)
        return Rgb(r, g, b, 1.0)

    @cache
    def lighten(self, factor):
        def lighten(u):
            return clamp(u - u * factor, 0.0, 1.0)

        return Cmyk(lighten(self.c), lighten(self.m), lighten(self.y), lighten(self.k))

    @cache
    def darken(self, factor):
        def darken(u):
            return clamp(u + (1.0 - u) * factor, 0.0, 1.0)

        return Cmyk(darken(self.c), darken(self.m), darken(self.y), darken(self.k))


def rgb(r, g, b):
    return Rgb(r / 255, g / 255, b / 255)


def clamp(x, minv, maxv):
    return max(minv, min(x, maxv))


def path(points, fill="none", fill_opacity=1, stroke="black", stroke_width=.5):
    return f"""<path d="{' '.join(points)} z" stroke="{stroke}" stroke-width="{stroke_width}" fill="{fill}" fill-opacity="{fill_opacity}" />"""


def voxel(x0, y0, z0, x1, y1, z1, color):
    scale = 1
    sin = .5
    cos = math.sqrt(3) / 2

    def isometric_projection(x, y, z):
        return f"{200 + (x - y) * cos * scale} {240 + ((x + y - 2 * z) * sin * scale)}"

    def M(point):
        return f"M {point}"

    def L(point):
        return f"L {point}"

    face_a = [
        M(isometric_projection(x0, y0, z1)),
        L(isometric_projection(x1, y0, z1)),
        L(isometric_projection(x1, y1, z1)),
        L(isometric_projection(x0, y1, z1))
    ]

    face_b = [
        M(isometric_projection(x1, y0, z0)),
        L(isometric_projection(x1, y1, z0)),
        L(isometric_projection(x1, y1, z1)),
        L(isometric_projection(x1, y0, z1)),
    ]

    face_c = [
        M(isometric_projection(x0, y1, z0)),
        L(isometric_projection(x1, y1, z0)),
        L(isometric_projection(x1, y1, z1)),
        L(isometric_projection(x0, y1, z1)),
    ]

    return (
            path(face_b, fill=color.darken(20 / 100)) +
            path(face_c, fill=color.lighten(10 / 100)) +
            path(face_a, fill=color.lighten(50 / 100))
    )


def open_file_default(file_path):
    system_platform = platform.system()

    if system_platform == 'Windows':
        os.startfile(file_path)
    elif system_platform == 'Darwin':  # For macOS
        subprocess.Popen(['open', file_path])
    else:  # For Linux or other Unix-based systems
        subprocess.Popen(['xdg-open', file_path])


COLORS = [
    rgb(0, 0, 0)
]

MAX_TRUCK_DIMENSIONS = Dimension("400x210x220")

COLORS = {
    "K": (0, 0, 0),
    "R": (255, 0, 0),
    "G": (0, 255, 0),
    "W": (255, 255, 255),
    "C": (255, 179, 126),
    "Y": (255, 255, 0),
}

if __name__ == '__main__':

    svg_content = []
    svg_content.append("""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="560">""")
    blocks = []
    i = 0
    for (i, line) in enumerate(open("santa.txt", "r").readlines()):
        for (j, char) in enumerate(line):
            if char in COLORS:
                (r, g, b) = COLORS[char]
                blocks.append((i, (i * 10, 180 - (j * 10), 0, i * 10 + 10, 180 - (j * 10) + 10, 10, r, g, b)))

    blocks.sort(key=lambda block: (block[1][0] + block[1][1], block[1][2]))
    for (i, (x0, y0, z0, x1, y1, z1, r, g, b)) in blocks:
        for x in range(x0, x1, 10):
            for y in range(y0, y1, 10):
                for z in range(z0, z1, 10):
                    svg_content.append(voxel(x, y, z, x + 10, y + 10, z + 10, rgb(r, g, b)))
    svg_content.append("</svg>")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        f.write("\n".join(svg_content) + "\n")
        output = f.name

    open_file_default(output)


