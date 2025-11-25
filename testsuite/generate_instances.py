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
    
    # Cas simples
    generator.generate_instance("bronze_easy_01", "bronze", 42)
    generator.generate_instance("bronze_easy_02", "bronze", 123)
    generator.generate_instance("bronze_easy_03", "bronze", 456)
    
    # Cas avec colis variés
    generator.generate_instance("bronze_varied_01", "bronze", 789)
    generator.generate_instance("bronze_varied_02", "bronze", 1011)
    
    # Cas dense (colis grands)
    generator.generate_instance("bronze_dense", "bronze", 2000,
                              max_item_dims="300x300x300")
    
    # Cas sparse (petits colis)
    generator.generate_instance("bronze_sparse", "bronze", 2001,
                              max_item_dims="100x100x100")
    
    # Cas avec véhicule petit
    generator.generate_instance("bronze_small_truck", "bronze", 2002,
                              max_truck_dims="100x100x100")
    
    # ============ SILVER LEAGUE (≤100 colis) ============
    print("\n=== SILVER LEAGUE ===")
    
    # Instances standard
    for i, seed in enumerate([3000, 3100, 3200, 3300, 3400], 1):
        generator.generate_instance(f"silver_standard_{i:02d}", "silver", seed)
    
    # Cas dense
    generator.generate_instance("silver_dense_01", "silver", 4000,
                              max_item_dims="350x350x350")
    generator.generate_instance("silver_dense_02", "silver", 4001,
                              max_item_dims="400x400x400")
    
    # Cas sparse
    generator.generate_instance("silver_sparse_01", "silver", 4100,
                              max_item_dims="150x150x150")
    generator.generate_instance("silver_sparse_02", "silver", 4101,
                              max_item_dims="100x100x100")
    
    # Cas avec colis allongés (simulation)
    generator.generate_instance("silver_elongated_01", "silver", 4200,
                              max_item_dims="500x200x200")
    generator.generate_instance("silver_elongated_02", "silver", 4201,
                              max_item_dims="450x150x150")
    
    # Cas avec colis plats
    generator.generate_instance("silver_flat_01", "silver", 4300,
                              max_item_dims="400x400x100")
    generator.generate_instance("silver_flat_02", "silver", 4301,
                              max_item_dims="450x450x50")
    
    # Cas avec petit véhicule (difficile)
    generator.generate_instance("silver_small_truck", "silver", 4400,
                              max_truck_dims="150x150x150")
    
    # Cas avec grand véhicule (facile)
    generator.generate_instance("silver_large_truck", "silver", 4500,
                              max_truck_dims="400x400x400")
    
    # ============ GOLD LEAGUE (≤1000 colis) ============
    print("\n=== GOLD LEAGUE ===")
    
    # Instances standard
    for i, seed in enumerate([5000, 5100, 5200, 5300, 5400], 1):
        generator.generate_instance(f"gold_standard_{i:02d}", "gold", seed)
    
    # Tests de scalabilité
    for i, seed in enumerate([6000, 6100, 6200], 1):
        generator.generate_instance(f"gold_scalability_{i:02d}", "gold", seed)
    
    # Cas dense (difficile)
    generator.generate_instance("gold_dense_01", "gold", 7000,
                              max_item_dims="400x400x400")
    generator.generate_instance("gold_dense_02", "gold", 7001,
                              max_item_dims="450x450x450")
    
    # Cas sparse (facile)
    generator.generate_instance("gold_sparse_01", "gold", 7100,
                              max_item_dims="100x100x100")
    generator.generate_instance("gold_sparse_02", "gold", 7101,
                              max_item_dims="150x150x150")
    
    # Cas mixtes (réaliste)
    generator.generate_instance("gold_mixed_01", "gold", 7200,
                              max_item_dims="350x350x350")
    generator.generate_instance("gold_mixed_02", "gold", 7201,
                              max_item_dims="300x300x300")
    
    # Cas avec contraintes de temps (Gold uniquement)
    generator.generate_instance("gold_timed_01", "gold", 8000)
    generator.generate_instance("gold_timed_02", "gold", 8001)
    generator.generate_instance("gold_timed_03", "gold", 8002)
    
    # Cas extrêmes
    generator.generate_instance("gold_extreme_dense", "gold", 9000,
                              max_item_dims="490x490x490")
    generator.generate_instance("gold_extreme_sparse", "gold", 9100,
                              max_item_dims="50x50x50")
    
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
