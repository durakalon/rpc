"""
Générateur d'instances de test pour le problème de bin packing 3D
Crée des jeux de tests variés pour évaluer les différents solveurs
"""

import sys
import os
from pathlib import Path
import subprocess
import json

# Ajouter le dossier parent au path pour utiliser generate.py
sys.path.insert(0, str(Path(__file__).parent.parent))


class InstanceGenerator:
    """Générateur d'instances de test avec caractéristiques contrôlées"""
    
    def __init__(self, output_dir: str = "instances"):
        self.output_dir = Path(output_dir)
        self.generate_script = Path(__file__).parent.parent / "generate.py"
        self.instances_metadata = []
    
    def generate_instance(self, name: str, league: str, seed: int, 
                         max_truck_dims: str = None, max_item_dims: str = None):
        """
        Génère une instance avec le script generate.py
        
        Args:
            name: Nom du fichier (sans extension)
            league: bronze, silver ou gold
            seed: Graine pour la génération
            max_truck_dims: Dimensions max du véhicule (ex: "400x210x220")
            max_item_dims: Dimensions max des colis (ex: "500x500x500")
        """
        league_dir = self.output_dir / league
        league_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = league_dir / f"{name}.txt"
        
        # Construire la commande
        cmd = [
            "python",
            str(self.generate_script),
            "--league", league,
            "--seed", str(seed)
        ]
        
        if max_truck_dims:
            cmd.extend(["--max-truck-dimensions", max_truck_dims])
        if max_item_dims:
            cmd.extend(["--max-item-dimensions", max_item_dims])
        
        # Exécuter et sauvegarder
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            
            # Sauvegarder les métadonnées
            metadata = {
                'name': name,
                'league': league,
                'seed': seed,
                'file': str(output_file.relative_to(self.output_dir.parent)),
                'max_truck_dims': max_truck_dims,
                'max_item_dims': max_item_dims
            }
            self.instances_metadata.append(metadata)
            
            print(f"[OK] Genere: {output_file.relative_to(self.output_dir.parent)}")
            return True
        else:
            print(f"[ERR] Erreur lors de la generation de {name}: {result.stderr}")
            return False
    
    def generate_likely_sat_instance(self, name: str, league: str, num_items: int,
                             vehicle_size: tuple, with_time: bool = False):
        """
        Génère une instance probablement SAT (mais pas garanti)
        
        Stratégie: on génère des items de petite taille pour augmenter la probabilité SAT
        - Items petits (max 30% des dimensions du véhicule)
        - Volume total < 40% du volume du véhicule
        ATTENTION: Cela n'est PAS une garantie (bin packing 3D NP-complet)
        """
        league_dir = self.output_dir / league
        league_dir.mkdir(parents=True, exist_ok=True)
        output_file = league_dir / f"{name}.txt"
        
        import random
        random.seed(hash(name))
        
        vx, vy, vz = vehicle_size
        
        # Écrire le véhicule
        lines = [f"{vx} {vy} {vz}"]
        lines.append(str(num_items))
        
        # Générer des items qui tiennent
        max_item_x = min(vx * 0.3, 150)
        max_item_y = min(vy * 0.3, 150)
        max_item_z = min(vz * 0.3, 150)
        
        for i in range(num_items):
            ix = random.randint(10, int(max_item_x)) // 10 * 10
            iy = random.randint(10, int(max_item_y)) // 10 * 10
            iz = random.randint(10, int(max_item_z)) // 10 * 10
            
            # Contrainte de temps pour Gold
            if league == "gold" and with_time:
                delivery = random.randint(0, 1000)
            else:
                delivery = -1
            
            lines.append(f"{ix} {iy} {iz} {delivery}")
        
        # Sauvegarder
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        
        metadata = {
            'name': name,
            'league': league,
            'type': 'likely_SAT',
            'num_items': num_items,
            'vehicle_size': vehicle_size,
            'file': str(output_file.relative_to(self.output_dir.parent))
        }
        self.instances_metadata.append(metadata)
        print(f"[OK] Genere: {output_file.relative_to(self.output_dir.parent)}")
        return True
    
    def generate_likely_unsat_instance(self, name: str, league: str, num_items: int,
                               vehicle_size: tuple, item_scale: float = 2.0):
        """
        Génère une instance probablement UNSAT (mais pas garanti)
        
        Stratégie: items volontairement grands ou nombreux
        - Items de taille moyenne = vehicle_size / sqrt(num_items) * item_scale
        - item_scale > 3.0 rend UNSAT très probable (mais pas certain)
        ATTENTION: Même avec un gros item_scale, un solveur efficace peut trouver SAT
        """
        league_dir = self.output_dir / league
        league_dir.mkdir(parents=True, exist_ok=True)
        output_file = league_dir / f"{name}.txt"
        
        import random
        import math
        random.seed(hash(name))
        
        vx, vy, vz = vehicle_size
        
        # Écrire le véhicule
        lines = [f"{vx} {vy} {vz}"]
        lines.append(str(num_items))
        
        # Items volontairement trop grands
        avg_size = (vx + vy + vz) / 3.0 / math.sqrt(num_items) * item_scale
        
        for i in range(num_items):
            ix = int(random.uniform(avg_size * 0.8, avg_size * 1.2)) // 10 * 10
            iy = int(random.uniform(avg_size * 0.8, avg_size * 1.2)) // 10 * 10
            iz = int(random.uniform(avg_size * 0.8, avg_size * 1.2)) // 10 * 10
            
            # Assurer les contraintes min/max
            ix = max(10, min(ix, 500))
            iy = max(10, min(iy, 500))
            iz = max(10, min(iz, 500))
            
            delivery = -1
            lines.append(f"{ix} {iy} {iz} {delivery}")
        
        # Sauvegarder
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        
        metadata = {
            'name': name,
            'league': league,
            'type': 'likely_UNSAT',
            'num_items': num_items,
            'vehicle_size': vehicle_size,
            'item_scale': item_scale,
            'file': str(output_file.relative_to(self.output_dir.parent))
        }
        self.instances_metadata.append(metadata)
        print(f"[OK] Genere: {output_file.relative_to(self.output_dir.parent)}")
        return True
    
    
    def save_metadata(self, filename: str = "instances_metadata.json"):
        """Sauvegarde les métadonnées de toutes les instances"""
        metadata_file = self.output_dir / filename
        with open(metadata_file, 'w') as f:
            json.dump(self.instances_metadata, f, indent=2)
        print(f"\n[OK] Metadonnees sauvegardees: {metadata_file}")


def generate_test_suite():
    """Génère une suite complète de tests variés"""
    
    generator = InstanceGenerator(output_dir="instances")
    
    print("="*60)
    print("     Generation de la Test Suite RPC")
    print("="*60 + "\n")
    
    # ============ BRONZE LEAGUE (≤10 colis) ============
    print("\n=== BRONZE LEAGUE ===")
    
    # Instances aléatoires (generate.py)
    print("  [Random instances]")
    generator.generate_instance("bronze_random_01", "bronze", 42)
    generator.generate_instance("bronze_random_02", "bronze", 123)
    generator.generate_instance("bronze_random_03", "bronze", 456)
    generator.generate_instance("bronze_random_04", "bronze", 789)
    generator.generate_instance("bronze_random_05", "bronze", 1011)
    
    # Instances probablement SAT (items petits)
    print("  [Likely SAT instances]")
    generator.generate_likely_sat_instance("bronze_likely_sat_01", "bronze", num_items=5, 
                                   vehicle_size=(200, 150, 150))
    generator.generate_likely_sat_instance("bronze_likely_sat_02", "bronze", num_items=8,
                                   vehicle_size=(300, 200, 200))
    generator.generate_likely_sat_instance("bronze_likely_sat_03", "bronze", num_items=3,
                                   vehicle_size=(150, 150, 150))
    
    # Instances probablement UNSAT (items très grands)
    print("  [Likely UNSAT instances]")
    generator.generate_likely_unsat_instance("bronze_likely_unsat_01", "bronze", num_items=10,
                                     vehicle_size=(100, 100, 100), item_scale=3.5)
    generator.generate_likely_unsat_instance("bronze_likely_unsat_02", "bronze", num_items=8,
                                     vehicle_size=(80, 80, 80), item_scale=3.0)
    
    # ============ SILVER LEAGUE (≤100 colis) ============
    print("\n=== SILVER LEAGUE ===")
    
    # Instances aléatoires
    print("  [Random instances]")
    for i, seed in enumerate([3000, 3100, 3200, 3300, 3400], 1):
        generator.generate_instance(f"silver_random_{i:02d}", "silver", seed)
    
    # Instances probablement SAT (items petits)
    print("  [Likely SAT instances]")
    generator.generate_likely_sat_instance("silver_likely_sat_01", "silver", num_items=30,
                                   vehicle_size=(350, 250, 250))
    generator.generate_likely_sat_instance("silver_likely_sat_02", "silver", num_items=50,
                                   vehicle_size=(400, 300, 280))
    generator.generate_likely_sat_instance("silver_likely_sat_03", "silver", num_items=20,
                                   vehicle_size=(300, 200, 200))
    generator.generate_likely_sat_instance("silver_likely_sat_04", "silver", num_items=70,
                                   vehicle_size=(400, 350, 300))
    
    # Instances probablement UNSAT (items trop grands ou trop nombreux)
    print("  [Likely UNSAT instances]")
    generator.generate_likely_unsat_instance("silver_likely_unsat_01", "silver", num_items=80,
                                     vehicle_size=(200, 150, 150), item_scale=3.0)
    generator.generate_likely_unsat_instance("silver_likely_unsat_02", "silver", num_items=60,
                                     vehicle_size=(180, 180, 180), item_scale=2.8)
    generator.generate_likely_unsat_instance("silver_likely_unsat_03", "silver", num_items=100,
                                     vehicle_size=(150, 150, 150), item_scale=3.5)
    
    # ============ GOLD LEAGUE (≤1000 colis) ============
    print("\n=== GOLD LEAGUE ===")
    
    # Instances aléatoires
    print("  [Random instances]")
    for i, seed in enumerate([5000, 5100, 5200, 5300, 5400], 1):
        generator.generate_instance(f"gold_random_{i:02d}", "gold", seed)
    
    # Instances probablement SAT (items petits)
    print("  [Likely SAT instances]")
    generator.generate_likely_sat_instance("gold_likely_sat_01", "gold", num_items=200,
                                   vehicle_size=(400, 350, 300))
    generator.generate_likely_sat_instance("gold_likely_sat_02", "gold", num_items=400,
                                   vehicle_size=(450, 400, 350))
    generator.generate_likely_sat_instance("gold_likely_sat_03", "gold", num_items=100,
                                   vehicle_size=(350, 300, 250))
    generator.generate_likely_sat_instance("gold_likely_sat_04", "gold", num_items=600,
                                   vehicle_size=(500, 450, 400))
    
    # Instance petite pour vérification manuelle
    print("  [Manual verification instance]")
    generator.generate_likely_sat_instance("gold_manual_check", "gold", num_items=100,
                                   vehicle_size=(300, 250, 200), with_time=True)
    
    # Instances probablement UNSAT (items très grands)
    print("  [Likely UNSAT instances]")
    generator.generate_likely_unsat_instance("gold_likely_unsat_01", "gold", num_items=500,
                                     vehicle_size=(250, 200, 200), item_scale=3.5)
    generator.generate_likely_unsat_instance("gold_likely_unsat_02", "gold", num_items=800,
                                     vehicle_size=(300, 250, 250), item_scale=3.0)
    generator.generate_likely_unsat_instance("gold_likely_unsat_03", "gold", num_items=1000,
                                     vehicle_size=(200, 200, 200), item_scale=4.0)
    
    # Tests de scalabilité (avec contraintes de temps)
    print("  [Scalability instances]")
    generator.generate_likely_sat_instance("gold_likely_scale_01", "gold", num_items=300,
                                   vehicle_size=(400, 350, 300), with_time=True)
    generator.generate_likely_sat_instance("gold_likely_scale_02", "gold", num_items=700,
                                   vehicle_size=(450, 400, 350), with_time=True)
    generator.generate_likely_sat_instance("gold_likely_scale_03", "gold", num_items=1000,
                                   vehicle_size=(500, 450, 400), with_time=True)
    
    # Sauvegarder les métadonnées
    generator.save_metadata()
    
    print("\n" + "="*60)
    print(f"[OK] Generation terminee: {len(generator.instances_metadata)} instances creees")
    print("="*60)


def list_instances():
    """Liste toutes les instances générées"""
    instances_dir = Path("instances")
    
    if not instances_dir.exists():
        print("Aucune instance trouvée. Lancez d'abord la génération.")
        return
    
    print("\n" + "="*60)
    print("            Instances de Test Disponibles")
    print("="*60 + "\n")
    
    for league in ["bronze", "silver", "gold"]:
        league_dir = instances_dir / league
        if league_dir.exists():
            instances = sorted(league_dir.glob("*.txt"))
            print(f"\n{league.upper()} ({len(instances)} instances):")
            for inst in instances:
                size = inst.stat().st_size
                print(f"  - {inst.name:40s} ({size:>6d} bytes)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Générateur d'instances de test")
    parser.add_argument("--generate", action="store_true", 
                       help="Générer toutes les instances")
    parser.add_argument("--list", action="store_true",
                       help="Lister les instances existantes")
    parser.add_argument("--clean", action="store_true",
                       help="Nettoyer les instances existantes")
    
    args = parser.parse_args()
    
    if args.clean:
        import shutil
        instances_dir = Path("instances")
        if instances_dir.exists():
            shutil.rmtree(instances_dir)
            print("[OK] Instances nettoyees")
    
    if args.generate:
        generate_test_suite()
    
    if args.list:
        list_instances()
    
    if not any([args.generate, args.list, args.clean]):
        parser.print_help()
