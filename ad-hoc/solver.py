"""
Solveur ad-hoc
Optimise le nombre de véhicules utilisés pour transporter des colis
"""

import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class SortingHeuristic(Enum):
    """Heuristiques de tri pour les colis"""
    VOLUME_DECREASING = "volume"
    LONGEST_SIDE_DECREASING = "longest_side"
    AREA_DECREASING = "area"
    HEIGHT_DECREASING = "height"


@dataclass
class Item:
    """Représente un colis à livrer"""
    id: int
    length: int  # L - longueur
    width: int   # W - largeur
    height: int  # H - hauteur
    delivery_time: int  # D - temps de livraison (-1 si pas de contrainte)
    
    @property
    def volume(self) -> int:
        """Volume du colis"""
        return self.length * self.width * self.height
    
    @property
    def base_area(self) -> int:
        """Surface de base du colis"""
        return self.length * self.width
    
    @property
    def dimensions(self) -> Tuple[int, int, int]:
        """Dimensions du colis"""
        return (self.length, self.width, self.height)
    
    def __repr__(self) -> str:
        return f"Item({self.id}, {self.length}x{self.width}x{self.height}, D={self.delivery_time})"


@dataclass
class Vehicle:
    """Représente un véhicule disponible"""
    length: int  # L - longueur
    width: int   # W - largeur  
    height: int  # H - hauteur
    
    @property
    def volume(self) -> int:
        """Volume du véhicule"""
        return self.length * self.width * self.height
    
    @property
    def dimensions(self) -> Tuple[int, int, int]:
        """Dimensions du véhicule"""
        return (self.length, self.width, self.height)
    
    def __repr__(self) -> str:
        return f"Vehicle({self.length}x{self.width}x{self.height})"


@dataclass
class Placement:
    """Représente le placement d'un colis dans un véhicule"""
    vehicle_id: int  # Numéro du véhicule (0-indexed)
    item_id: int     # Numéro du colis
    x: int           # Position x (coin inférieur gauche avant)
    y: int           # Position y
    z: int           # Position z
    length: int      # L du colis
    width: int       # W du colis
    height: int      # H du colis
    
    def occupies_space(self, x: int, y: int, z: int) -> bool:
        """Vérifie si ce placement occupe l'espace donné"""
        return (self.x <= x < self.x + self.length and
                self.y <= y < self.y + self.width and
                self.z <= z < self.z + self.height)
    
    def overlaps_with(self, other: 'Placement') -> bool:
        """Vérifie si deux placements se chevauchent"""
        return not (self.x + self.length <= other.x or other.x + other.length <= self.x or
                    self.y + self.width <= other.y or other.y + other.width <= self.y or
                    self.z + self.height <= other.z or other.z + other.height <= self.z)
    
    def __repr__(self) -> str:
        return f"Placement(V{self.vehicle_id}, Item{self.item_id}, ({self.x},{self.y},{self.z}))"


class VehiclePacker:
    """Gère le remplissage d'un véhicule unique"""
    
    def __init__(self, vehicle: Vehicle, vehicle_id: int):
        self.vehicle = vehicle
        self.vehicle_id = vehicle_id
        self.placements: List[Placement] = []
        self.occupied_volume = 0
        
    @property
    def available_volume(self) -> int:
        """Volume restant disponible"""
        return self.vehicle.volume - self.occupied_volume
    
    @property
    def utilization_rate(self) -> float:
        """Taux d'utilisation du véhicule"""
        return self.occupied_volume / self.vehicle.volume if self.vehicle.volume > 0 else 0.0
    
    def can_fit_item(self, item: Item) -> bool:
        """Vérifie si le colis peut théoriquement rentrer dans le véhicule"""
        # Vérifier toutes les orientations possibles
        dimensions = [
            (item.length, item.width, item.height),
            (item.length, item.height, item.width),
            (item.width, item.length, item.height),
            (item.width, item.height, item.length),
            (item.height, item.length, item.width),
            (item.height, item.width, item.length),
        ]
        
        for l, w, h in dimensions:
            if (l <= self.vehicle.length and 
                w <= self.vehicle.width and 
                h <= self.vehicle.height):
                return True
        return False
    
    def find_placement_position(self, item: Item) -> Optional[Tuple[int, int, int, int, int, int]]:
        """
        Trouve une position pour placer le colis dans le véhicule
        Retourne (x, y, z, l, w, h) ou None si impossible
        """
        # Essayer toutes les orientations possibles
        orientations = [
            (item.length, item.width, item.height),
            (item.length, item.height, item.width),
            (item.width, item.length, item.height),
            (item.width, item.height, item.length),
            (item.height, item.length, item.width),
            (item.height, item.width, item.length),
        ]
        
        # Points candidats pour le placement (coins des colis existants + origine)
        candidate_positions = [(0, 0, 0)]
        
        for placement in self.placements:
            # Ajouter les coins potentiels
            candidate_positions.extend([
                (placement.x + placement.length, placement.y, placement.z),
                (placement.x, placement.y + placement.width, placement.z),
                (placement.x, placement.y, placement.z + placement.height),
            ])
        
        # Trier les positions candidates (stratégie bottom-left-back)
        candidate_positions.sort(key=lambda pos: (pos[2], pos[1], pos[0]))
        
        # Essayer chaque orientation à chaque position candidate
        for l, w, h in orientations:
            # Vérifier que les dimensions rentrent dans le véhicule
            if l > self.vehicle.length or w > self.vehicle.width or h > self.vehicle.height:
                continue
                
            for x, y, z in candidate_positions:
                # Vérifier que le colis ne dépasse pas du véhicule
                if (x + l > self.vehicle.length or 
                    y + w > self.vehicle.width or 
                    z + h > self.vehicle.height):
                    continue
                
                # Vérifier qu'il n'y a pas de chevauchement avec les colis existants
                test_placement = Placement(self.vehicle_id, item.id, x, y, z, l, w, h)
                if not any(test_placement.overlaps_with(p) for p in self.placements):
                    return (x, y, z, l, w, h)
        
        return None
    
    def add_item(self, item: Item) -> bool:
        """
        Tente d'ajouter un colis au véhicule
        Retourne True si succès, False sinon
        """
        position = self.find_placement_position(item)
        if position is None:
            return False
        
        x, y, z, l, w, h = position
        placement = Placement(self.vehicle_id, item.id, x, y, z, l, w, h)
        self.placements.append(placement)
        self.occupied_volume += item.volume
        
        return True


class BinPackingSolver:
    """Solveur principal pour le problème de bin packing 3D"""
    
    def __init__(self, vehicle: Vehicle, items: List[Item], 
                 heuristic: SortingHeuristic = SortingHeuristic.VOLUME_DECREASING):
        self.vehicle_template = vehicle
        self.items = items
        self.heuristic = heuristic
        self.vehicles: List[VehiclePacker] = []
        self.unplaced_items: List[Item] = []
        
    def sort_items(self) -> List[Item]:
        """Trie les colis selon l'heuristique choisie"""
        if self.heuristic == SortingHeuristic.VOLUME_DECREASING:
            return sorted(self.items, key=lambda item: item.volume, reverse=True)
        elif self.heuristic == SortingHeuristic.LONGEST_SIDE_DECREASING:
            return sorted(self.items, key=lambda item: max(item.dimensions), reverse=True)
        elif self.heuristic == SortingHeuristic.AREA_DECREASING:
            return sorted(self.items, key=lambda item: item.base_area, reverse=True)
        elif self.heuristic == SortingHeuristic.HEIGHT_DECREASING:
            return sorted(self.items, key=lambda item: item.height, reverse=True)
        else:
            return self.items.copy()
    
    def solve(self) -> bool:
        """
        Résout le problème de bin packing
        Retourne True si tous les colis ont été placés, False sinon
        """
        sorted_items = self.sort_items()
        
        for item in sorted_items:
            placed = False
            
            # Essayer de placer dans un véhicule existant
            for vehicle_packer in self.vehicles:
                if vehicle_packer.add_item(item):
                    placed = True
                    break
            
            # Si pas placé, créer un nouveau véhicule
            if not placed:
                new_vehicle = VehiclePacker(self.vehicle_template, len(self.vehicles))
                if new_vehicle.add_item(item):
                    self.vehicles.append(new_vehicle)
                    placed = True
                else:
                    # Le colis ne rentre dans aucun véhicule (même vide)
                    self.unplaced_items.append(item)
        
        return len(self.unplaced_items) == 0
    
    def get_all_placements(self) -> List[Placement]:
        """Récupère tous les placements de tous les véhicules"""
        all_placements = []
        for vehicle_packer in self.vehicles:
            all_placements.extend(vehicle_packer.placements)
        return all_placements
    
    def get_statistics(self) -> dict:
        """Retourne les statistiques de la solution"""
        return {
            'nb_vehicles_used': len(self.vehicles),
            'nb_items_placed': sum(len(v.placements) for v in self.vehicles),
            'nb_items_unplaced': len(self.unplaced_items),
            'total_items': len(self.items),
            'average_utilization': sum(v.utilization_rate for v in self.vehicles) / len(self.vehicles) if self.vehicles else 0.0,
            'total_volume_used': sum(v.occupied_volume for v in self.vehicles),
            'total_volume_available': sum(v.vehicle.volume for v in self.vehicles),
        }


def parse_input(input_text: str) -> Tuple[Vehicle, List[Item]]:
    """
    Parse le format d'entrée
    Format:
    L W H (dimensions du véhicule)
    N (nombre de colis)
    L1 W1 H1 D1 (dimensions et temps de livraison pour chaque colis)
    ...
    """
    lines = input_text.strip().split('\n')
    
    # Ligne 1: dimensions du véhicule
    vehicle_dims = list(map(int, lines[0].split()))
    vehicle = Vehicle(vehicle_dims[0], vehicle_dims[1], vehicle_dims[2])
    
    # Ligne 2: nombre de colis
    nb_items = int(lines[1])
    
    # Lignes suivantes: colis
    items = []
    for i in range(nb_items):
        item_data = list(map(int, lines[2 + i].split()))
        item = Item(
            id=i,
            length=item_data[0],
            width=item_data[1],
            height=item_data[2],
            delivery_time=item_data[3] if len(item_data) > 3 else -1
        )
        items.append(item)
    
    return vehicle, items


def format_output(solver: BinPackingSolver) -> str:
    """
    Formate la sortie selon le format attendu
    Format:
    SAT ou UNSAT
    V X Y Z L W H (pour chaque colis si SAT)
    """
    if solver.unplaced_items:
        return "UNSAT"
    
    lines = ["SAT"]
    placements = solver.get_all_placements()
    
    # Trier par ID de colis pour respecter l'ordre
    placements.sort(key=lambda p: p.item_id)
    
    for placement in placements:
        line = f"{placement.vehicle_id} {placement.x} {placement.y} {placement.z} " \
               f"{placement.x + placement.length} {placement.y + placement.width} " \
               f"{placement.z + placement.height}"
        lines.append(line)
    
    return '\n'.join(lines)


def solve_problem(input_text: str, heuristic: SortingHeuristic = SortingHeuristic.VOLUME_DECREASING, 
                  verbose: bool = False) -> str:
    """
    Fonction principale pour résoudre le problème
    """
    # Parser l'entrée
    vehicle, items = parse_input(input_text)
    
    if verbose:
        print(f"Véhicule: {vehicle}", file=sys.stderr)
        print(f"Nombre de colis: {len(items)}", file=sys.stderr)
        print(f"Volume total des colis: {sum(item.volume for item in items)}", file=sys.stderr)
        print(f"Volume du véhicule: {vehicle.volume}", file=sys.stderr)
        print(f"Heuristique: {heuristic.value}", file=sys.stderr)
    
    # Résoudre
    solver = BinPackingSolver(vehicle, items, heuristic)
    success = solver.solve()
    
    if verbose:
        stats = solver.get_statistics()
        print(f"\n=== Résultats ===", file=sys.stderr)
        print(f"Succès: {success}", file=sys.stderr)
        print(f"Véhicules utilisés: {stats['nb_vehicles_used']}", file=sys.stderr)
        print(f"Colis placés: {stats['nb_items_placed']}/{stats['total_items']}", file=sys.stderr)
        print(f"Taux d'utilisation moyen: {stats['average_utilization']:.2%}", file=sys.stderr)
        if solver.vehicles:
            for i, v in enumerate(solver.vehicles):
                print(f"  Véhicule {i}: {len(v.placements)} colis, {v.utilization_rate:.2%} rempli", 
                      file=sys.stderr)
    
    # Formater la sortie
    return format_output(solver)


if __name__ == "__main__":
    # Lecture depuis stdin
    input_text = sys.stdin.read()
    
    # Résolution avec heuristique par défaut
    result = solve_problem(input_text, heuristic=SortingHeuristic.VOLUME_DECREASING, verbose=False)
    
    # Affichage du résultat
    print(result)
