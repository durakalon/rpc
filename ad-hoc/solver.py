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
    orientations: List[Tuple[int, int, int]] = None  # Toutes les orientations valides (précomputées)
    
    def __post_init__(self):
        """Précalcule toutes les orientations valides pour ce colis"""
        if self.orientations is None:
            # Génère les 6 orientations possibles (permutations des dimensions)
            all_orientations = [
                (self.length, self.width, self.height),
                (self.length, self.height, self.width),
                (self.width, self.length, self.height),
                (self.width, self.height, self.length),
                (self.height, self.length, self.width),
                (self.height, self.width, self.length),
            ]
            # Supprime les doublons (pour les cubes ou dimensions égales)
            self.orientations = list(set(all_orientations))
    
    def filter_orientations(self, vehicle: 'Vehicle') -> List[Tuple[int, int, int]]:
        """Filtre les orientations qui peuvent rentrer dans le véhicule"""
        valid = []
        for l, w, h in self.orientations:
            if l <= vehicle.length and w <= vehicle.width and h <= vehicle.height:
                valid.append((l, w, h))
        return valid
    
    @property
    def volume(self) -> int:
        """Volume du colis"""
        return self.length * self.width * self.height
    
    @property
    def base_area(self) -> int:
        """Surface de base du colis"""
        return self.length * self.width
    
    @property
    def longest_side(self) -> int:
        """Côté le plus long du colis"""
        return max(self.length, self.width, self.height)
    
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
    
    def __init__(self, vehicle: Vehicle, vehicle_id: int, delivery_zone: Optional[Tuple[int, int]] = None):
        self.vehicle = vehicle
        self.vehicle_id = vehicle_id
        self.placements: List[Placement] = []
        self.occupied_volume = 0
        # Contraintes de zone de livraison : (x_min, x_max) pour l'ordre de livraison basé sur la longueur
        # None signifie aucune contrainte
        self.delivery_zone = delivery_zone
        
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
        # Utilise les orientations précomputées
        valid_orientations = item.filter_orientations(self.vehicle)
        return len(valid_orientations) > 0
    
    def find_placement_position(self, item: Item, x_min: Optional[int] = None, 
                                x_max: Optional[int] = None) -> Optional[Tuple[int, int, int, int, int, int]]:
        """
        Trouve une position pour placer le colis dans le véhicule
        Retourne (x, y, z, l, w, h) ou None si impossible
        
        Args:
            item: Colis à placer
            x_min: Position x minimale (pour les contraintes de zone de livraison)
            x_max: Position x maximale (pour les contraintes de zone de livraison)
        """
        # Utilise les orientations précomputées, filtrées pour ce véhicule
        orientations = item.filter_orientations(self.vehicle)
        
        if not orientations:
            return None
        
        # Points candidats pour le placement (coins des colis existants + origine)
        candidate_positions = set([(0, 0, 0)])
        
        for placement in self.placements:
            # Ajouter les coins potentiels
            candidate_positions.add((placement.x + placement.length, placement.y, placement.z))
            candidate_positions.add((placement.x, placement.y + placement.width, placement.z))
            candidate_positions.add((placement.x, placement.y, placement.z + placement.height))
        
        # Convertir en liste et filtrer les positions invalides
        candidate_list = []
        for x, y, z in candidate_positions:
            # Filtrer par zone de livraison si spécifié
            if x_min is not None and x < x_min:
                continue
            if x_max is not None and x >= x_max:
                continue
            if x < self.vehicle.length and y < self.vehicle.width and z < self.vehicle.height:
                candidate_list.append((x, y, z))
        
        # Trier les positions candidates (stratégie bottom-left-back)
        candidate_list.sort(key=lambda pos: (pos[2], pos[1], pos[0]))
        
        # Essayer chaque orientation à chaque position candidate
        for l, w, h in orientations:
            for x, y, z in candidate_list:
                # Appliquer les contraintes de zone
                if x_min is not None and x < x_min:
                    continue
                if x_max is not None and x + l > x_max:
                    continue
            
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
    
    def add_item(self, item: Item, x_min: Optional[int] = None, 
                 x_max: Optional[int] = None) -> bool:
        """
        Tente d'ajouter un colis au véhicule
        Retourne True si succès, False sinon
        
        Args:
            item: Colis à ajouter
            x_min: Position x minimale (pour les contraintes de zone de livraison)
            x_max: Position x maximale (pour les contraintes de zone de livraison)
        """
        position = self.find_placement_position(item, x_min, x_max)
        if position is None:
            return False
        
        x, y, z, l, w, h = position
        placement = Placement(self.vehicle_id, item.id, x, y, z, l, w, h)
        self.placements.append(placement)
        self.occupied_volume += item.volume
        
        return True
    
    def try_add_item_with_score(self, item: Item, x_min: Optional[int] = None,
                                x_max: Optional[int] = None) -> Optional[float]:
        """
        Teste si on peut ajouter le colis et retourne un score sans modifier l'état
        Retourne le score (taux d'utilisation après ajout) si possible, None sinon
        """
        position = self.find_placement_position(item, x_min, x_max)
        if position is None:
            return None
        
        # Score = taux d'utilisation après ajout (plus élevé = meilleur)
        new_occupied = self.occupied_volume + item.volume
        return new_occupied / self.vehicle.volume if self.vehicle.volume > 0 else 0.0
    
    def remove_item(self, item_id: int) -> bool:
        """
        Retire un colis du véhicule
        Retourne True si le colis a été trouvé et retiré, False sinon
        """
        for i, placement in enumerate(self.placements):
            if placement.item_id == item_id:
                self.occupied_volume -= (placement.length * placement.width * placement.height)
                self.placements.pop(i)
                return True
        return False


class BinPackingSolver:
    """Solveur principal pour le problème de bin packing 3D"""
    
    def __init__(self, vehicle: Vehicle, items: List[Item], 
                 heuristic: SortingHeuristic = SortingHeuristic.VOLUME_DECREASING,
                 use_delivery_zones: bool = True):
        self.vehicle_template = vehicle
        self.items = items
        self.heuristic = heuristic
        self.vehicles: List[VehiclePacker] = []
        self.unplaced_items: List[Item] = []
        self.use_delivery_zones = use_delivery_zones
        # Gestion de l'ordre de livraison
        self.delivery_groups: dict = {}  # temps_de_livraison -> liste de colis
        self.delivery_zones: dict = {}  # temps_de_livraison -> (x_min, x_max)
        self._compute_delivery_groups()
        
    def _compute_delivery_groups(self):
        """Groupe les colis par temps de livraison et calcule les zones spatiales"""
        if not self.use_delivery_zones:
            return
        
        # Grouper les colis par temps de livraison
        for item in self.items:
            d = item.delivery_time
            if d not in self.delivery_groups:
                self.delivery_groups[d] = []
            self.delivery_groups[d].append(item)
        
        # Calculer les zones : les colis livrés en premier (D plus petit) vont à l'arrière du camion (x plus grand)
        # Stratégie adaptative selon la fragmentation des groupes de livraison
        constrained_times = sorted([d for d in self.delivery_groups.keys() if d >= 0])
        
        if not constrained_times:
            return
        
        nb_groups = len(constrained_times)
        nb_constrained_items = sum(len(self.delivery_groups[d]) for d in constrained_times)
        
        # Calculer le volume total par temps de livraison
        volumes = {}
        total_constrained_volume = 0
        for d in constrained_times:
            vol = sum(item.volume for item in self.delivery_groups[d])
            volumes[d] = vol
            total_constrained_volume += vol
        
        # Si forte fragmentation (beaucoup de groupes avec peu de colis chacun),
        # utiliser une stratégie de zones cumulatives plus souples
        avg_items_per_group = nb_constrained_items / nb_groups if nb_groups > 0 else 0
        
        if nb_groups > 20 or (nb_groups > 10 and avg_items_per_group < 3):
            # STRATÉGIE CUMULATIVE : zones qui se chevauchent avec contrainte d'ordre relatif
            # Les colis avec D petit (livrés tôt) peuvent accéder à plus d'espace vers l'arrière
            # Les colis avec D grand (livrés tard) sont restreints à l'avant
            for i, d in enumerate(constrained_times):
                # Calcul de la position relative dans l'ordre de livraison (0 = premier, 1 = dernier)
                relative_pos = i / max(nb_groups - 1, 1)
                
                # x_min = 0 pour tous (permet flexibilité)
                # x_max dépend de la position : livraisons tardives limitées, précoces étendues
                # Premier livré (relative_pos=0) : peut aller jusqu'à 100% du camion
                # Dernier livré (relative_pos=1) : limité à ~40% du camion
                x_min = 0
                x_max = int(self.vehicle_template.length * (0.4 + 0.6 * (1 - relative_pos)))
                
                self.delivery_zones[d] = (x_min, x_max)
        else:
            # STRATÉGIE STANDARD : zones proportionnelles avec taille minimale garantie
            # Utilisée quand il y a peu de groupes ou beaucoup de colis par groupe
            current_x = 0
            for d in reversed(constrained_times):  # Commencer par la livraison la plus tardive
                if total_constrained_volume > 0:
                    # Allocation proportionnelle au volume du groupe
                    zone_length = int((volumes[d] / total_constrained_volume) * self.vehicle_template.length * 0.85)
                    
                    # Garantir une taille minimale raisonnable basée sur les colis du groupe
                    items_in_group = self.delivery_groups[d]
                    max_item_dimension = max(max(item.length, item.width, item.height) for item in items_in_group)
                    min_zone_length = max_item_dimension * 3  # Au moins 3x la plus grande dimension
                    
                    zone_length = max(zone_length, min_zone_length)
                else:
                    zone_length = self.vehicle_template.length // nb_groups
                
                # S'assurer que la zone ne dépasse pas la longueur disponible
                zone_length = min(zone_length, self.vehicle_template.length - current_x)
                
                x_max = min(current_x + zone_length, self.vehicle_template.length)
                self.delivery_zones[d] = (current_x, x_max)
                current_x = x_max
        
        # Les colis non contraints (D=-1) peuvent utiliser tout l'espace
        if -1 in self.delivery_groups:
            self.delivery_zones[-1] = (0, self.vehicle_template.length)
    
    def _get_zone_for_item(self, item: Item) -> Optional[Tuple[int, int]]:
        """Obtient les contraintes de zone x pour un colis basé sur son temps de livraison"""
        if not self.use_delivery_zones:
            return None
        
        d = item.delivery_time
        if d in self.delivery_zones:
            return self.delivery_zones[d]
        return None
    
    def sort_items(self) -> List[Item]:
        """Trie les colis selon l'heuristique choisie et les contraintes de livraison"""
        # Clé de tri secondaire basée sur l'heuristique
        def secondary_key(item: Item):
            if self.heuristic == SortingHeuristic.VOLUME_DECREASING:
                return -item.volume
            elif self.heuristic == SortingHeuristic.LONGEST_SIDE_DECREASING:
                return -item.longest_side
            elif self.heuristic == SortingHeuristic.AREA_DECREASING:
                return -item.base_area
            elif self.heuristic == SortingHeuristic.HEIGHT_DECREASING:
                return -item.height
            else:
                return 0
        
        # Tri primaire : temps de livraison (colis contraints d'abord, par D croissant)
        # Tri secondaire : heuristique
        def sort_key(item: Item):
            # Placer les colis contraints (D >= 0) avant les non contraints (D = -1)
            # Pour les contraints : trier par D croissant
            # Pour les non contraints : viennent en dernier
            if item.delivery_time >= 0:
                primary = (0, item.delivery_time)  # Contraint, ordonné par D
            else:
                primary = (1, 0)  # Non contraint, à la fin
            
            return (primary, secondary_key(item))
        
        return sorted(self.items, key=sort_key)
    
    def solve(self) -> bool:
        """
        Résout le problème de bin packing avec Best-Fit et contraintes de livraison
        Retourne True si tous les colis ont été placés, False sinon
        """
        sorted_items = self.sort_items()
        
        for item in sorted_items:
            placed = False
            zone = self._get_zone_for_item(item)
            x_min, x_max = zone if zone else (None, None)
            
            # Best-Fit: essayer tous les véhicules et choisir le meilleur
            best_vehicle = None
            best_score = -1.0
            
            for vehicle_packer in self.vehicles:
                score = vehicle_packer.try_add_item_with_score(item, x_min, x_max)
                if score is not None and score > best_score:
                    best_score = score
                    best_vehicle = vehicle_packer
            
            # Si un véhicule convient, y placer le colis
            if best_vehicle is not None:
                if best_vehicle.add_item(item, x_min, x_max):
                    placed = True
    
            # Si pas placé, créer un nouveau véhicule
            if not placed:
                new_vehicle = VehiclePacker(self.vehicle_template, len(self.vehicles))
                if new_vehicle.add_item(item, x_min, x_max):
                    self.vehicles.append(new_vehicle)
                    placed = True
                else:
                    # Le colis ne rentre dans aucun véhicule (même vide)
                    self.unplaced_items.append(item)
        
        # Apply local search to reduce number of vehicles
        if len(self.unplaced_items) == 0:
            self._local_search_close_vehicles()
        
        return len(self.unplaced_items) == 0
    
    def _local_search_close_vehicles(self, max_iterations: int = 10):
        """
        Recherche locale : essaie de fermer des véhicules en redistribuant les colis
        """
        iteration = 0
        while iteration < max_iterations:
            improved = self._try_close_one_vehicle()
            if not improved:
                break
            iteration += 1
    
    def _try_close_one_vehicle(self) -> bool:
        """
        Tente de fermer le véhicule le moins rempli en déplaçant ses colis vers d'autres véhicules
        Retourne True si un véhicule a été fermé avec succès
        """
        if len(self.vehicles) <= 1:
            return False
        
        # Trouver le véhicule avec le plus petit taux d'utilisation
        min_util = float('inf')
        target_vehicle_idx = -1
        
        for i, vehicle in enumerate(self.vehicles):
            if vehicle.utilization_rate < min_util:
                min_util = vehicle.utilization_rate
                target_vehicle_idx = i
        
        if target_vehicle_idx < 0:
            return False
        
        target_vehicle = self.vehicles[target_vehicle_idx]
        items_to_move = []
        
        # Extraire tous les colis du véhicule cible
        for placement in target_vehicle.placements:
            # Trouver le colis original
            item = next((it for it in self.items if it.id == placement.item_id), None)
            if item:
                items_to_move.append(item)
        
        # Essayer de placer tous les colis dans d'autres véhicules
        temp_placements = []  # Stocker les placements réussis
        
        for item in items_to_move:
            zone = self._get_zone_for_item(item)
            x_min, x_max = zone if zone else (None, None)
            
            placed = False
            best_vehicle = None
            best_score = -1.0
            
            # Essayer tous les véhicules sauf celui ciblé
            for i, vehicle_packer in enumerate(self.vehicles):
                if i == target_vehicle_idx:
                    continue
                
                score = vehicle_packer.try_add_item_with_score(item, x_min, x_max)
                if score is not None and score > best_score:
                    best_score = score
                    best_vehicle = vehicle_packer
            
            if best_vehicle is not None:
                temp_placements.append((best_vehicle, item, x_min, x_max))
            else:
                # Impossible de placer tous les colis, abandonner
                return False
        
        # Tous les colis peuvent être placés, appliquer les changements
        for vehicle_packer, item, x_min, x_max in temp_placements:
            vehicle_packer.add_item(item, x_min, x_max)
        
        # Retirer le véhicule cible
        self.vehicles.pop(target_vehicle_idx)
        
        # Renuméroter les véhicules
        for i, vehicle in enumerate(self.vehicles):
            vehicle.vehicle_id = i
            for placement in vehicle.placements:
                placement.vehicle_id = i
        
        return True
    
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
    
    def validate_solution(self, verbose: bool = False) -> bool:
        """
        Valide la solution pour vérifier sa correction
        Retourne True si la solution est valide, False sinon
        """
        valid = True
        
        # Vérifier tous les placements
        for vehicle in self.vehicles:
            for placement in vehicle.placements:
                # Vérifier les limites
                if not (0 <= placement.x and placement.x + placement.length <= vehicle.vehicle.length):
                    if verbose:
                        print(f"ERROR: Item {placement.item_id} exceeds vehicle length bounds", file=sys.stderr)
                    valid = False
                
                if not (0 <= placement.y and placement.y + placement.width <= vehicle.vehicle.width):
                    if verbose:
                        print(f"ERROR: Item {placement.item_id} exceeds vehicle width bounds", file=sys.stderr)
                    valid = False
                
                if not (0 <= placement.z and placement.z + placement.height <= vehicle.vehicle.height):
                    if verbose:
                        print(f"ERROR: Item {placement.item_id} exceeds vehicle height bounds", file=sys.stderr)
                    valid = False
                
                # Vérifier les chevauchements avec d'autres colis dans le même véhicule
                for other in vehicle.placements:
                    if placement.item_id != other.item_id and placement.overlaps_with(other):
                        if verbose:
                            print(f"ERROR: Items {placement.item_id} and {other.item_id} overlap", file=sys.stderr)
                        valid = False
        
        # Vérifier les contraintes d'ordre de livraison (vérification basique)
        if self.use_delivery_zones and verbose:
            for vehicle in self.vehicles:
                delivery_positions = {}  # temps_de_livraison -> liste de positions (x, z)
                
                for placement in vehicle.placements:
                    item = next((it for it in self.items if it.id == placement.item_id), None)
                    if item and item.delivery_time >= 0:
                        d = item.delivery_time
                        if d not in delivery_positions:
                            delivery_positions[d] = []
                        delivery_positions[d].append((placement.x, placement.z))
                
                # Vérifier que les livraisons plus tôt sont plus à l'arrière (x plus grand) en moyenne
                delivery_times = sorted(delivery_positions.keys())
                for i in range(len(delivery_times) - 1):
                    d1, d2 = delivery_times[i], delivery_times[i + 1]
                    avg_x1 = sum(x for x, z in delivery_positions[d1]) / len(delivery_positions[d1])
                    avg_x2 = sum(x for x, z in delivery_positions[d2]) / len(delivery_positions[d2])
                    if avg_x1 < avg_x2:
                        if verbose:
                            print(f"WARNING: Delivery order may be violated: D={d1} avg_x={avg_x1:.1f} vs D={d2} avg_x={avg_x2:.1f}", file=sys.stderr)
        
        return valid


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
                  verbose: bool = False, validate: bool = False) -> str:
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
    
    # Validate solution if requested
    if validate or verbose:
        is_valid = solver.validate_solution(verbose=verbose)
        if verbose:
            print(f"Solution valide: {is_valid}", file=sys.stderr)
    
    # Formater la sortie
    return format_output(solver)


if __name__ == "__main__":
    # Lecture depuis stdin
    input_text = sys.stdin.read()
    
    # Résolution avec heuristique par défaut
    result = solve_problem(input_text, heuristic=SortingHeuristic.VOLUME_DECREASING, verbose=False)
    
    # Affichage du résultat
    print(result)
