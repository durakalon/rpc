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


def path(points, fill=None, fill_opacity=None, stroke=None, stroke_width=None, stroke_linejoin=None,
         stroke_linecap=None, paint_order=None):
    attrs = {
        "fill": fill,
        "fill-opacity": fill_opacity,
        "stroke": stroke,
        "stroke-width": stroke_width,
        "stroke-linejoin": stroke_linejoin,
        "stroke-linecap": stroke_linecap,
        "paint-order": paint_order,
    }
    return f"""<path d="{' '.join(points)} z" {' '.join(f'{k}="{v}"' for (k, v) in attrs.items() if v is not None)} />"""

def is_on_left(other, item):
    (x0, y0, z0, x1, y1, z1) = range(6)
    return (other[x0], other[y0], other[z0]) == (item[x0], item[y1], item[z0])
def is_in_front_of(other, item):
    (x0, y0, z0, x1, y1, z1) = range(6)
    return (other[x0], other[y0], other[z0]) == (item[x1], item[y0], item[z0])
def is_above(other, item):
    (x0, y0, z0, x1, y1, z1) = range(6)
    return (other[x0], other[y0], other[z0]) == (item[x0], item[y0], item[z1])

def is_hidden(item, others):
    return any([ is_on_left(o[0], item) for o in others ]) and any([ is_in_front_of(o[0], item) for o in others ]) and any([ is_above(o[0], item) for o in others ])

def voxel(x0, y0, z0, x1, y1, z1, color, shape):
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

    xpz = [
        M(isometric_projection(x1, y0, z0)),
        L(isometric_projection(x1, y1, z0)),
    ]

    xpy = [
        M(isometric_projection(x1, y0, z0)),
        L(isometric_projection(x1, y0, z1)),
    ]

    xpzp = [
        M(isometric_projection(x1, y0, z1)),
        L(isometric_projection(x1, y1, z1)),
    ]

    yzp = [
        M(isometric_projection(x0, y0, z1)),
        L(isometric_projection(x1, y0, z1)),
    ]

    xzp = [
        M(isometric_projection(x0, y0, z1)),
        L(isometric_projection(x0, y1, z1)),
    ]

    ypzp = [
        M(isometric_projection(x0, y1, z1)),
        L(isometric_projection(x1, y1, z1)),
    ]

    ypz = [
        M(isometric_projection(x0, y1, z0)),
        L(isometric_projection(x1, y1, z0)),
    ]

    xyp = [
        M(isometric_projection(x0, y1, z0)),
        L(isometric_projection(x0, y1, z1)),
    ]

    xpyp = [
        M(isometric_projection(x1, y1, z0)),
        L(isometric_projection(x1, y1, z1)),
    ]

    front_color = color.darken(20 / 100)
    top_color = color.lighten(50 / 100)
    left_color = color.lighten(10 / 100)
    (X0, Y0, Z0, X1, Y1, Z1) = shape

    args = {
        "fill": "none",
        "stroke_linejoin": "round",
        "paint_order": "stroke",
    }
    color = color.darken(50 / 100)

    return "\n".join([
        path(face_b, fill=front_color),
        path(xpz, stroke=color if (x1 == X1 and z0 == Z0) else front_color, stroke_width=1 if (x1 == X1 and z0 == Z0) else 0, **args),
        path(xpy, stroke=color if (x1 == X1 and y0 == Y0) else front_color, stroke_width=1 if (x1 == X1 and y0 == Y0) else 0, **args),
        path(face_c, fill=left_color),
        path(xyp, stroke=color if (x0 == X0 and y1 == Y1) else left_color, stroke_width=1 if (x0 == X0 and y1 == Y1) else 0, **args),
        path(ypz, stroke=color if (y1 == Y1 and z0 == Z0) else left_color, stroke_width=1 if (y1 == Y1 and z0 == Z0) else 0, **args),
        path(xpyp, stroke=color if (x1 == X1 and y1 == Y1) else left_color, stroke_width=1 if (x1 == X1 and y1 == Y1) else 0, **args),
        path(face_a, fill=top_color),
        path(xpzp, stroke=color if (x1 == X1 and z1 == Z1) else top_color, stroke_width=1 if (x1 == X1 and z1 == Z1) else 0, **args),
        path(xzp, stroke=color if (x0 == X0 and z1 == Z1) else top_color, stroke_width=1 if (x0 == X0 and z1 == Z1) else 0, **args),
        path(yzp, stroke=color if (y0 == Y0 and z1 == Z1) else top_color, stroke_width=1 if (y0 == Y0 and z1 == Z1) else 0, **args),
        path(ypzp, stroke=color if (y1 == Y1 and z1 == Z1) else top_color, stroke_width=1 if (y1 == Y1 and z1 == Z1) else 0, **args),
    ])


def open_file_default(file_path):
    system_platform = platform.system()

    if system_platform == 'Windows':
        os.startfile(file_path)
    elif system_platform == 'Darwin':  # For macOS
        subprocess.Popen(['open', file_path])
    else:  # For Linux or other Unix-based systems
        subprocess.Popen(['xdg-open', file_path])


COLORS = [
    rgb(208, 118, 223),
    rgb(83, 187, 82),
    rgb(143, 84, 203),
    rgb(185, 179, 53),
    rgb(83, 106, 215),
    rgb(127, 166, 60),
    rgb(200, 64, 168),
    rgb(102, 185, 131),
    rgb(215, 58, 122),
    rgb(63, 191, 188),
    rgb(206, 59, 70),
    rgb(93, 161, 216),
    rgb(218, 91, 48),
    rgb(140, 140, 225),
    rgb(218, 143, 53),
    rgb(85, 104, 169),
    rgb(206, 168, 105),
    rgb(144, 79, 152),
    rgb(70, 121, 61),
    rgb(227, 118, 170),
    rgb(132, 113, 45),
    rgb(200, 144, 204),
    rgb(166, 87, 52),
    rgb(159, 71, 101),
    rgb(225, 128, 125)
]

MAX_TRUCK_DIMENSIONS = Dimension("400x210x220")

if __name__ == "__main__":
    parser = argparse.ArgumentParser("visualize.py")
    parser.add_argument("input", nargs="?", type=argparse.FileType("r"), default=sys.stdin,
                        help="Le fichier d'entrée (utilise stdin par défaut)")
    parser.add_argument("--truck-no", type=int, default=0, dest="truck_no", help="Le numéro du véhicule à visualiser")
    parser.add_argument("--truck-dimensions", type=Dimension, default=MAX_TRUCK_DIMENSIONS,
                        dest="truck_dimensions", help="Dimensions du véhicule")

    args = parser.parse_args()

    svg_content = []
    svg_content.append("""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="560">""")
    blocks = []
    first = True
    i = 0
    for (i, line) in enumerate(args.input):
        if first:
            first = False
            if line == "SAT\n":
                continue
            elif line == "UNSAT\n":
                exit(0)
            else:
                raise ValueError("Invalid input")
        if line == "\n":
            break
        (truck, x0, y0, z0, x1, y1, z1) = map(int, line.split(" "))
        if truck != args.truck_no:
            continue
        blocks.append((i, (x0, y0, z0, x1, y1, z1)))
        i += 1
    (L, W, H) = args.truck_dimensions
    # Drawing the truck
    svg_content.append(voxel(-2, 0, 0, 0, H + 10, W + 10, rgb(64, 64, 64), (0, 0, 0, L, H, W)))
    svg_content.append(voxel(0, -2, 0, L + 10, 0, W + 10, rgb(32, 32, 32), (0, 0, 0, L, H, W)))
    svg_content.append(voxel(0, 0, -2, L + 10, H + 10, 0, rgb(0, 0, 0), (0, 0, 0, L, H, W)))
    for y in range(0, W, 10):
        for z in range(0, H, 10):
            pass
            # svg_content.append(voxel(-2, y, z, 0, y + 10, z + 10, rgb(64, 64, 64), (0, 0, 0, L, H, W)))
    for x in range(0, L, 10):
        for z in range(0, H, 10):
            pass
            # svg_content.append(voxel(x, -2, z, x + 10, 0, z + 10, rgb(32, 32, 32), (0, 0, 0, L, H, W)))
        for y in range(0, W, 10):
            pass
            # svg_content.append(voxel(x, y, -2, x + 10, y + 10, 0, rgb(0, 0, 0), (0, 0, 0, L, H, W)))
    # Drawing the blocks
    voxels = []
    for (i, (x0, y0, z0, x1, y1, z1)) in blocks:
        for x in range(x0, x1, 10):
            for y in range(y0, y1, 10):
                for z in range(z0, z1, 10):
                    voxels.append(((x, y, z, x + 10, y + 10, z + 10),
                                   voxel(x, y, z, x + 10, y + 10, z + 10, COLORS[i % len(COLORS)],
                                         (x0, y0, z0, x1, y1, z1))))
    voxels.sort(key=lambda it: (it[0][0] + it[0][1], it[0][2]))

    visible_voxels = [ i for i in voxels if not is_hidden(i[0], voxels) ]

    for voxel in visible_voxels:
        (coord, shape) = voxel
        svg_content.append(shape)
    svg_content.append("</svg>")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        f.write("\n".join(svg_content) + "\n")
        output = f.name

    open_file_default(output)
