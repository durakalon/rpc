import argparse


def prng():
    # generate a random number between 0 and 1 from the seed
    global seed
    seed = ((0xadb4a92d * seed) + 9999999) & 0xFFFFFFFF
    return seed >> 16


def prng_range(min, max):
    return min + prng() % (max - min)


def generate_vehicle(x, y, z):
    return [(prng_range(x[0], x[1] + 1) // 10) * 10, (prng_range(y[0], y[1] + 1) // 10) * 10,
            (prng_range(z[0], z[1] + 1) // 10) * 10]


def generate_item(x, y, z, d):
    return [(prng_range(x[0], x[1] + 1) // 10) * 10, (prng_range(y[0], y[1] + 1) // 10) * 10,
            (prng_range(z[0], z[1] + 1) // 10) * 10, prng_range(d[0], d[1] + 1)]


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


MIN_TRUCK_DIMENSIONS = Dimension("20x20x20")
MAX_TRUCK_DIMENSIONS = Dimension("400x210x220")
MIN_ITEM_DIMENSIONS = Dimension("10x10x10")
MAX_ITEM_DIMENSIONS = Dimension("500x500x500")

if __name__ == "__main__":
    parser = argparse.ArgumentParser("generate.py")
    parser.add_argument("--league", type=str, choices=["bronze", "silver", "gold"], default="bronze", help="Le niveau de la league")
    parser.add_argument("--seed", type=int, default=42, help="Graine pour le générateur de nombres aléatoires")
    parser.add_argument("--max-truck-dimensions", type=Dimension, default=MAX_TRUCK_DIMENSIONS,
                        dest="max_truck_dimensions", help="Dimensions maximales des véhicules")
    parser.add_argument("--max-item-dimensions", type=Dimension, default=MAX_ITEM_DIMENSIONS,
                        dest="max_item_dimensions", help="Dimensions maximales des objets")

    args = parser.parse_args()
    seed = args.seed
    max_nb_items = 10
    max_delivery_time = -1
    if args.league == "bronze":
        pass
    elif args.league == "silver":
        max_nb_items = 100
    else:  # gold
        max_nb_items = 1000
        max_delivery_time = 1000

    (L1_min, W1_min, Z1_min) = MIN_TRUCK_DIMENSIONS
    (L1_max, W1_max, Z1_max) = args.max_truck_dimensions
    assert L1_max <= MAX_TRUCK_DIMENSIONS.x and W1_max <= MAX_TRUCK_DIMENSIONS.y and Z1_max <= MAX_TRUCK_DIMENSIONS.z
    print(*generate_vehicle([L1_min, L1_max], [W1_min, W1_max], [Z1_min, Z1_max]))

    (L2_min, W2_min, Z2_min) = MIN_ITEM_DIMENSIONS
    (L2_max, W2_max, Z2_max) = args.max_item_dimensions
    assert L2_max <= MAX_ITEM_DIMENSIONS.x and W2_max <= MAX_ITEM_DIMENSIONS.y and Z2_max <= MAX_ITEM_DIMENSIONS.z
    nb_items = prng_range(1, max_nb_items + 1)
    print(nb_items)
    for i in range(nb_items):
        print(*generate_item([L2_min, L2_max], [W2_min, W2_max], [Z2_min, Z2_max], [-1, max_delivery_time]))
