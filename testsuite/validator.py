"""
Validateur de solutions pour le problème de bin packing 3D
Vérifie qu'une solution respecte toutes les contraintes du problème
"""

import sys
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class Vehicle:
    length: int
    width: int
    height: int


@dataclass
class Item:
    id: int
    length: int
    width: int
    height: int
    delivery_time: int


@dataclass
class ItemPlacement:
    vehicle_id: int
    item_id: int
    x1: int
    y1: int
    z1: int
    x2: int
    y2: int
    z2: int
    
    @property
    def length(self) -> int:
        return self.x2 - self.x1
    
    @property
    def width(self) -> int:
        return self.y2 - self.y1
    
    @property
    def height(self) -> int:
        return self.z2 - self.z1


class SolutionValidator:
    """Valide une solution de bin packing 3D"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
    
    def parse_input(self, input_file: str) -> Tuple[Vehicle, List[Item]]:
        """Parse le fichier d'entrée"""
        with open(input_file, 'r') as f:
            lines = f.readlines()
        
        # Ligne 1: dimensions du véhicule
        vehicle_dims = list(map(int, lines[0].split()))
        vehicle = Vehicle(*vehicle_dims)
        
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
    
    def parse_output(self, output_file: str) -> Tuple[str, List[ItemPlacement]]:
        """Parse le fichier de sortie"""
        with open(output_file, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not lines:
            return "INVALID", []
        
        status = lines[0]
        if status not in ["SAT", "UNSAT"]:
            self.errors.append(f"Statut invalide: '{status}' (attendu: SAT ou UNSAT)")
            return "INVALID", []
        
        if status == "UNSAT":
            return "UNSAT", []
        
        # Parser les placements
        placements = []
        for i, line in enumerate(lines[1:], start=1):
            parts = list(map(int, line.split()))
            if len(parts) != 7:
                self.errors.append(f"Ligne {i+1}: format invalide (attendu: V X1 Y1 Z1 X2 Y2 Z2)")
                continue
            
            placement = ItemPlacement(
                vehicle_id=parts[0],
                item_id=i-1,  # ID implicite basé sur l'ordre
                x1=parts[1], y1=parts[2], z1=parts[3],
                x2=parts[4], y2=parts[5], z2=parts[6]
            )
            placements.append(placement)
        
        return status, placements
    
    def validate(self, input_file: str, output_file: str) -> bool:
        """
        Valide une solution complète
        Retourne True si valide, False sinon
        """
        self.errors = []
        self.warnings = []
        
        try:
            vehicle, items = self.parse_input(input_file)
            status, placements = self.parse_output(output_file)
        except Exception as e:
            self.errors.append(f"Erreur de parsing: {e}")
            return False
        
        if status == "INVALID":
            return False
        
        if status == "UNSAT":
            if self.verbose:
                print("  Solution déclarée UNSAT (non validation effectuée)")
            return True
        
        # Vérifications pour SAT
        if not self._check_all_items_placed(items, placements):
            return False
        
        if not self._check_item_dimensions(items, placements):
            return False
        
        if not self._check_vehicle_bounds(vehicle, placements):
            return False
        
        if not self._check_no_overlaps(placements):
            return False
        
        if not self._check_positive_dimensions(placements):
            return False
        
        return len(self.errors) == 0
    
    def _check_all_items_placed(self, items: List[Item], placements: List[ItemPlacement]) -> bool:
        """Vérifie que tous les colis sont placés"""
        if len(placements) != len(items):
            self.errors.append(
                f"Nombre de placements incorrect: {len(placements)} (attendu: {len(items)})"
            )
            return False
        return True
    
    def _check_item_dimensions(self, items: List[Item], placements: List[ItemPlacement]) -> bool:
        """Vérifie que les dimensions des placements correspondent aux colis"""
        valid = True
        for placement in placements:
            item = items[placement.item_id]
            placed_dims = sorted([placement.length, placement.width, placement.height])
            item_dims = sorted([item.length, item.width, item.height])
            
            if placed_dims != item_dims:
                self.errors.append(
                    f"Colis {placement.item_id}: dimensions incorrectes "
                    f"{placed_dims} != {item_dims}"
                )
                valid = False
        
        return valid
    
    def _check_vehicle_bounds(self, vehicle: Vehicle, placements: List[ItemPlacement]) -> bool:
        """Vérifie que tous les colis restent dans les limites du véhicule"""
        valid = True
        for placement in placements:
            if placement.x1 < 0 or placement.x2 > vehicle.length:
                self.errors.append(
                    f"Colis {placement.item_id} dépasse en X: [{placement.x1}, {placement.x2}] "
                    f"(limite: {vehicle.length})"
                )
                valid = False
            
            if placement.y1 < 0 or placement.y2 > vehicle.width:
                self.errors.append(
                    f"Colis {placement.item_id} dépasse en Y: [{placement.y1}, {placement.y2}] "
                    f"(limite: {vehicle.width})"
                )
                valid = False
            
            if placement.z1 < 0 or placement.z2 > vehicle.height:
                self.errors.append(
                    f"Colis {placement.item_id} dépasse en Z: [{placement.z1}, {placement.z2}] "
                    f"(limite: {vehicle.height})"
                )
                valid = False
        
        return valid
    
    def _check_no_overlaps(self, placements: List[ItemPlacement]) -> bool:
        """Vérifie qu'il n'y a pas de chevauchements entre colis du même véhicule"""
        valid = True
        
        # Grouper par véhicule
        by_vehicle = {}
        for p in placements:
            if p.vehicle_id not in by_vehicle:
                by_vehicle[p.vehicle_id] = []
            by_vehicle[p.vehicle_id].append(p)
        
        # Vérifier les chevauchements dans chaque véhicule
        for vehicle_id, vehicle_placements in by_vehicle.items():
            for i, p1 in enumerate(vehicle_placements):
                for p2 in vehicle_placements[i+1:]:
                    if self._overlaps(p1, p2):
                        self.errors.append(
                            f"Chevauchement dans véhicule {vehicle_id}: "
                            f"colis {p1.item_id} et {p2.item_id}"
                        )
                        valid = False
        
        return valid
    
    def _overlaps(self, p1: ItemPlacement, p2: ItemPlacement) -> bool:
        """Vérifie si deux placements se chevauchent"""
        return not (p1.x2 <= p2.x1 or p2.x2 <= p1.x1 or
                    p1.y2 <= p2.y1 or p2.y2 <= p1.y1 or
                    p1.z2 <= p2.z1 or p2.z2 <= p1.z1)
    
    def _check_positive_dimensions(self, placements: List[ItemPlacement]) -> bool:
        """Vérifie que toutes les dimensions sont positives"""
        valid = True
        for placement in placements:
            if placement.length <= 0 or placement.width <= 0 or placement.height <= 0:
                self.errors.append(
                    f"Colis {placement.item_id}: dimensions non positives "
                    f"({placement.length}×{placement.width}×{placement.height})"
                )
                valid = False
        
        return valid
    
    def print_report(self):
        """Affiche un rapport de validation"""
        if not self.errors and not self.warnings:
            print("  [OK] Solution valide")
        else:
            if self.errors:
                print(f"  [ERR] {len(self.errors)} erreur(s):")
                for error in self.errors:
                    print(f"    - {error}")
            
            if self.warnings:
                print(f"  [WARN] {len(self.warnings)} avertissement(s):")
                for warning in self.warnings:
                    print(f"    - {warning}")


def validate_solution(input_file: str, output_file: str, verbose: bool = False) -> bool:
    """
    Fonction utilitaire pour valider une solution
    
    Args:
        input_file: Fichier d'entrée (.txt)
        output_file: Fichier de sortie (.txt)
        verbose: Afficher les détails
    
    Returns:
        True si la solution est valide
    """
    validator = SolutionValidator(verbose=verbose)
    
    if not Path(input_file).exists():
        print(f"[ERR] Fichier d'entree introuvable: {input_file}")
        return False
    
    if not Path(output_file).exists():
        print(f"[ERR] Fichier de sortie introuvable: {output_file}")
        return False
    
    is_valid = validator.validate(input_file, output_file)
    
    if verbose:
        validator.print_report()
    
    return is_valid


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validateur de solutions")
    parser.add_argument("-i", "--input", required=True, help="Fichier d'entrée")
    parser.add_argument("-o", "--output", required=True, help="Fichier de sortie")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    is_valid = validate_solution(args.input, args.output, args.verbose)
    
    sys.exit(0 if is_valid else 1)
