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

def get_projection_function(angle_type):
    """Retourne la fonction de projection isométrique selon l'angle choisi."""
    scale = 1
    sin = .5
    cos = math.sqrt(3) / 2
    
    if angle_type == "front":
        # Vue de face (angle par défaut)
        def projection(x, y, z):
            return f"{200 + (x - y) * cos * scale} {240 + ((x + y - 2 * z) * sin * scale)}"
    elif angle_type == "back":
        # Vue de dos (rotation 180°)
        def projection(x, y, z):
            return f"{200 + (y - x) * cos * scale} {240 + ((x + y - 2 * z) * sin * scale)}"
    elif angle_type == "left":
        # Vue de gauche (rotation 90° gauche)
        def projection(x, y, z):
            return f"{200 + (y + x) * cos * scale} {240 + ((y - x - 2 * z) * sin * scale)}"
    elif angle_type == "right":
        # Vue de droite (rotation 90° droite)
        def projection(x, y, z):
            return f"{200 + (-y - x) * cos * scale} {240 + ((x - y - 2 * z) * sin * scale)}"
    elif angle_type == "top":
        # Vue du dessus
        def projection(x, y, z):
            return f"{200 + (x - y) * cos * scale} {240 + ((x + y) * sin * scale - z * 1.5)}"
    else:
        # Par défaut: vue de face
        def projection(x, y, z):
            return f"{200 + (x - y) * cos * scale} {240 + ((x + y - 2 * z) * sin * scale)}"
    
    return projection

def voxel(x0, y0, z0, x1, y1, z1, color, shape, angle_type="front"):
    scale = 1
    sin = .5
    cos = math.sqrt(3) / 2

    isometric_projection = get_projection_function(angle_type)

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
    border_color = color.darken(50 / 100)

    return "\n".join([
        path(face_b, fill=front_color),
        path(xpz, stroke=border_color if (x1 == X1 and z0 == Z0) else front_color, stroke_width=1 if (x1 == X1 and z0 == Z0) else 0, **args),
        path(xpy, stroke=border_color if (x1 == X1 and y0 == Y0) else front_color, stroke_width=1 if (x1 == X1 and y0 == Y0) else 0, **args),
        path(face_c, fill=left_color),
        path(xyp, stroke=border_color if (x0 == X0 and y1 == Y1) else left_color, stroke_width=1 if (x0 == X0 and y1 == Y1) else 0, **args),
        path(ypz, stroke=border_color if (y1 == Y1 and z0 == Z0) else left_color, stroke_width=1 if (y1 == Y1 and z0 == Z0) else 0, **args),
        path(xpyp, stroke=border_color if (x1 == X1 and y1 == Y1) else left_color, stroke_width=1 if (x1 == X1 and y1 == Y1) else 0, **args),
        path(face_a, fill=top_color),
        path(xpzp, stroke=border_color if (x1 == X1 and z1 == Z1) else top_color, stroke_width=1 if (x1 == X1 and z1 == Z1) else 0, **args),
        path(xzp, stroke=border_color if (x0 == X0 and z1 == Z1) else top_color, stroke_width=1 if (x0 == X0 and z1 == Z1) else 0, **args),
        path(yzp, stroke=border_color if (y0 == Y0 and z1 == Z1) else top_color, stroke_width=1 if (y0 == Y0 and z1 == Z1) else 0, **args),
        path(ypzp, stroke=border_color if (y1 == Y1 and z1 == Z1) else top_color, stroke_width=1 if (y1 == Y1 and z1 == Z1) else 0, **args),
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

def get_color_from_gradient(index, total, colormap="viridis"):
    """
    Génère une couleur à partir d'un gradient progressif.
    
    Args:
        index: Position de l'élément (0-based)
        total: Nombre total d'éléments
        colormap: Type de gradient ('viridis', 'plasma', 'turbo', 'rainbow')
    
    Returns:
        Rgb: Couleur correspondante
    """
    if total <= 1:
        t = 0.5
    else:
        t = index / (total - 1)
    
    if colormap == "viridis":
        # Viridis: violet foncé -> vert -> jaune
        if t < 0.5:
            r = 0.267 + 0.105 * (t * 2)
            g = 0.005 + 0.557 * (t * 2)
            b = 0.329 + 0.256 * (t * 2)
        else:
            r = 0.372 + 0.622 * ((t - 0.5) * 2)
            g = 0.562 + 0.432 * ((t - 0.5) * 2)
            b = 0.585 - 0.585 * ((t - 0.5) * 2)
    elif colormap == "plasma":
        # Plasma: bleu foncé -> violet -> orange -> jaune
        if t < 0.33:
            r = 0.050 + 0.450 * (t / 0.33)
            g = 0.030 + 0.170 * (t / 0.33)
            b = 0.530 + 0.270 * (t / 0.33)
        elif t < 0.66:
            r = 0.500 + 0.400 * ((t - 0.33) / 0.33)
            g = 0.200 + 0.200 * ((t - 0.33) / 0.33)
            b = 0.800 - 0.300 * ((t - 0.33) / 0.33)
        else:
            r = 0.900 + 0.100 * ((t - 0.66) / 0.34)
            g = 0.400 + 0.500 * ((t - 0.66) / 0.34)
            b = 0.500 - 0.400 * ((t - 0.66) / 0.34)
    elif colormap == "turbo":
        # Turbo: bleu -> cyan -> vert -> jaune -> orange -> rouge
        if t < 0.2:
            r = 0.190 + 0.110 * (t / 0.2)
            g = 0.070 + 0.530 * (t / 0.2)
            b = 0.480 + 0.420 * (t / 0.2)
        elif t < 0.4:
            r = 0.300 + 0.200 * ((t - 0.2) / 0.2)
            g = 0.600 + 0.300 * ((t - 0.2) / 0.2)
            b = 0.900 - 0.400 * ((t - 0.2) / 0.2)
        elif t < 0.6:
            r = 0.500 + 0.400 * ((t - 0.4) / 0.2)
            g = 0.900 + 0.050 * ((t - 0.4) / 0.2)
            b = 0.500 - 0.400 * ((t - 0.4) / 0.2)
        elif t < 0.8:
            r = 0.900 + 0.080 * ((t - 0.6) / 0.2)
            g = 0.950 - 0.350 * ((t - 0.6) / 0.2)
            b = 0.100 - 0.050 * ((t - 0.6) / 0.2)
        else:
            r = 0.980 - 0.130 * ((t - 0.8) / 0.2)
            g = 0.600 - 0.300 * ((t - 0.8) / 0.2)
            b = 0.050 - 0.050 * ((t - 0.8) / 0.2)
    elif colormap == "rainbow":
        # Rainbow: rouge -> orange -> jaune -> vert -> bleu -> violet
        hue = t * 300  # 0 à 300 degrés (évite le retour au rouge)
        c = 0.8
        x = c * (1 - abs((hue / 60) % 2 - 1))
        if hue < 60:
            r, g, b = c, x, 0
        elif hue < 120:
            r, g, b = x, c, 0
        elif hue < 180:
            r, g, b = 0, c, x
        elif hue < 240:
            r, g, b = 0, x, c
        else:
            r, g, b = x, 0, c
        # Ajouter de la luminosité
        r, g, b = r + 0.2, g + 0.2, b + 0.2
    else:  # défaut: viridis
        r = 0.267 + 0.727 * t
        g = 0.005 + 0.989 * t
        b = 0.329 + 0.256 * t - 0.585 * (t ** 2)
    
    return rgb(int(r * 255), int(g * 255), int(b * 255))

def generate_legend(delivery_order_colors, svg_y_start=20, colormap_mode=False, total_items=0, colormap="viridis"):
    """Génère une légende SVG pour l'ordre de livraison."""
    legend_items = []
    legend_items.append(f'<text x="20" y="{svg_y_start}" font-family="Arial" font-size="14" font-weight="bold">Ordre de livraison:</text>')
    
    if colormap_mode and total_items > 0:
        # Mode gradient: afficher une barre de couleur continue
        gradient_height = min(total_items * 20, 400)
        
        # Créer un gradient SVG
        legend_items.append(f'<defs>')
        legend_items.append(f'  <linearGradient id="orderGradient" x1="0%" y1="0%" x2="0%" y2="100%">')
        
        # Ajouter des stops de couleur
        num_stops = min(total_items, 20)
        for i in range(num_stops):
            t = i / (num_stops - 1) if num_stops > 1 else 0
            color = get_color_from_gradient(i, num_stops, colormap)
            offset = int(t * 100)
            legend_items.append(f'    <stop offset="{offset}%" style="stop-color:rgb({int(color.r*255)},{int(color.g*255)},{int(color.b*255)});stop-opacity:1" />')
        
        legend_items.append(f'  </linearGradient>')
        legend_items.append(f'</defs>')
        
        # Dessiner la barre de gradient
        legend_items.append(f'<rect x="20" y="{svg_y_start + 25}" width="30" height="{gradient_height}" fill="url(#orderGradient)" stroke="black" stroke-width="1"/>')
        
        # Ajouter des labels
        legend_items.append(f'<text x="55" y="{svg_y_start + 35}" font-family="Arial" font-size="11">1er colis</text>')
        legend_items.append(f'<text x="55" y="{svg_y_start + 25 + gradient_height - 5}" font-family="Arial" font-size="11">{total_items}e colis</text>')
        if total_items > 2:
            mid = total_items // 2
            legend_items.append(f'<text x="55" y="{svg_y_start + 25 + gradient_height // 2 + 5}" font-family="Arial" font-size="10">{mid}e</text>')
    else:
        # Mode discret: afficher chaque colis individuellement
        for i, (order_index, color) in enumerate(delivery_order_colors.items()):
            y_pos = svg_y_start + 25 + (i * 25)
            legend_items.append(f'<rect x="20" y="{y_pos - 12}" width="15" height="15" fill="rgb({int(color.r*255)},{int(color.g*255)},{int(color.b*255)})" stroke="black" stroke-width="1"/>')
            legend_items.append(f'<text x="40" y="{y_pos}" font-family="Arial" font-size="12">Colis {order_index + 1}</text>')
    
    return "\n".join(legend_items)

def read_delivery_order(input_file_path):
    """Lit le fichier d'entrée pour obtenir l'ordre de livraison initial."""
    with open(input_file_path, 'r') as f:
        lines = f.readlines()
    
    # Skip first line (dimensions)
    # Second line is number of packages
    packages = []
    for i, line in enumerate(lines[2:]):
        if line.strip():
            packages.append(line.strip().split(' ')[-1])  # Valeur d'ordre de livraison
    
    return packages

if __name__ == "__main__":
    parser = argparse.ArgumentParser("visualize.py")
    parser.add_argument("input", nargs="?", type=argparse.FileType("r"), default=sys.stdin,
                        help="Le fichier d'entrée (utilise stdin par défaut)")
    parser.add_argument("--truck-no", type=int, default=0, dest="truck_no", help="Le numéro du véhicule à visualiser")
    parser.add_argument("--truck-dimensions", type=Dimension, default=MAX_TRUCK_DIMENSIONS,
                        dest="truck_dimensions", help="Dimensions du véhicule")
    parser.add_argument("--angle", type=str, default="front", choices=["front", "back", "left", "right", "top"],
                        help="Angle de vue (front, back, left, right, top)")
    parser.add_argument("--order-file", type=str, dest="order_file",
                        help="Fichier d'entrée contenant l'ordre de livraison initial")
    parser.add_argument("--show-order", action="store_true", dest="show_order",
                        help="Afficher l'ordre de livraison avec des couleurs et une légende")
    parser.add_argument("--colormap", type=str, default="viridis", 
                        choices=["viridis", "plasma", "turbo", "rainbow"],
                        help="Type de gradient de couleur pour l'ordre (viridis, plasma, turbo, rainbow)")

    args = parser.parse_args()

    # Lire l'ordre de livraison si demandé
    delivery_order = None
    if args.show_order and args.order_file:
        delivery_order = read_delivery_order(args.order_file)
    
    svg_width = 760 if args.show_order else 560
    svg_content = []
    svg_content.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="560">')
    blocks = []
    first = True
    i = 0
    block_index = 0
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
        blocks.append((block_index, (x0, y0, z0, x1, y1, z1)))
        block_index += 1
        i += 1
    (L, H, W) = args.truck_dimensions
    # Drawing the truck
    svg_content.append(voxel(-2, 0, 0, 0, H + 10, W + 10, rgb(64, 64, 64), (0, 0, 0, L, H, W), args.angle))
    svg_content.append(voxel(0, -2, 0, L + 10, 0, W + 10, rgb(32, 32, 32), (0, 0, 0, L, H, W), args.angle))
    svg_content.append(voxel(0, 0, -2, L + 10, H + 10, 0, rgb(0, 0, 0), (0, 0, 0, L, H, W), args.angle))
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
            # svg_content.append(voxel(x, y, -2, x + 10, y + 10, 0, rgb(0, 0, 0), (0, 0, 0, L, H, W), args.angle))
    # Drawing the blocks
    voxels = []
    delivery_order_colors = {}
    total_blocks = len(blocks)
    
    # Calculer les couleurs basées sur l'ordre de livraison
    if args.show_order and delivery_order:
        # Trier les delivery_order pour obtenir le rang de chaque colis
        # delivery_order[i] = temps de livraison du colis i
        # On veut colorer par rang (1er livré = couleur 0, 2e livré = couleur 1, etc.)
        order_values = [(i, int(delivery_order[i])) for i in range(len(delivery_order)) if i < total_blocks]
        sorted_by_delivery = sorted(order_values, key=lambda x: x[1])
        
        # Créer un mapping: index_colis -> rang dans l'ordre de livraison
        delivery_rank = {}
        for rank, (idx, _) in enumerate(sorted_by_delivery):
            delivery_rank[idx] = rank
    
    for (i, (x0, y0, z0, x1, y1, z1)) in blocks:
        # Choisir la couleur selon le mode
        if args.show_order and delivery_order and i < len(delivery_order):
            # Utiliser le rang de livraison pour la couleur
            rank = delivery_rank.get(i, i)
            color = get_color_from_gradient(rank, total_blocks, args.colormap)
            delivery_order_colors[i] = color
        else:
            # Mode normal: couleur par bloc
            color = COLORS[i % len(COLORS)]
        
        for x in range(x0, x1, 10):
            for y in range(y0, y1, 10):
                for z in range(z0, z1, 10):
                    voxels.append(((x, y, z, x + 10, y + 10, z + 10),
                                   voxel(x, y, z, x + 10, y + 10, z + 10, color,
                                         (x0, y0, z0, x1, y1, z1), args.angle)))
    voxels.sort(key=lambda it: (it[0][0] + it[0][1], it[0][2]))

    visible_voxels = [ i for i in voxels if not is_hidden(i[0], voxels) ]

    for voxel in visible_voxels:
        (coord, shape) = voxel
        svg_content.append(shape)
    
    # Ajouter la légende si demandé
    if args.show_order and delivery_order_colors:
        svg_content.append(generate_legend(delivery_order_colors, colormap_mode=True, 
                                          total_items=total_blocks, colormap=args.colormap))
    
    svg_content.append("</svg>")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        f.write("\n".join(svg_content) + "\n")
        output = f.name

    open_file_default(output)
