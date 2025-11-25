# Test Suite pour le Problème de Bin Packing 3D

## Vue d'ensemble

Cette test suite permet d'évaluer et de comparer différents solveurs pour le problème de bin packing 3D selon les critères du projet RPC.

### Objectifs

**Données et variables clairement définies**
**Contraintes spécifiées et transcrites**
**Comparaison de méthodes avec indicateurs variés**
**Format de sortie respecté**
**Démarche réplicable et facile d'utilisation**
**Jeux de tests avec passage à l'échelle**
**Hypothèses formulées sur l'efficacité**

## Structure

```
testsuite/
├── instances/              # Instances de test générées
│   ├── bronze/            # ≤10 colis
│   ├── silver/            # ≤100 colis
│   └── gold/              # ≤1000 colis
├── results/               # Résultats des solveurs
│   ├── ad-hoc/           # Résultats du solveur ad-hoc
│   └── generic/          # Résultats du solveur générique (futur)
├── benchmarks/            # Rapports de comparaison
├── generate_instances.py  # Génère les instances de test
├── validator.py           # Valide les solutions
├── run_tests.py           # Exécute les tests
├── compare_solvers.py     # Compare les solveurs
└── README.md              # Cette documentation
```

## Installation

Aucune dépendance externe. Python 3.7+ avec bibliothèque standard uniquement.

```bash
cd testsuite
```

## Utilisation

### 1. Générer les Instances de Test

```bash
# Générer toutes les instances (45+ instances)
python generate_instances.py --generate

# Lister les instances générées
python generate_instances.py --list

# Nettoyer et régénérer
python generate_instances.py --clean
python generate_instances.py --generate
```

**Instances générées :**

| League | Quantité | Caractéristiques |
|--------|----------|------------------|
| Bronze | ~8 | Easy, varied, dense, sparse, small_truck |
| Silver | ~16 | Standard, dense, sparse, elongated, flat, small/large truck |
| Gold | ~20+ | Standard, scalability, dense, sparse, mixed, timed, extreme |

### 2. Tester un Solveur

```bash
# Tester le solveur ad-hoc sur toutes les instances
python run_tests.py --solver ../ad-hoc/run.py --name ad-hoc -v

# Tester sur une league spécifique
python run_tests.py --solver ../ad-hoc/run.py --name ad-hoc --leagues bronze silver

# Avec timeout personnalisé (défaut: 300s)
python run_tests.py --solver ../ad-hoc/run.py --name ad-hoc --timeout 60
```

**Sortie générée :**
- Fichiers `.out` dans `results/ad-hoc/{league}/`
- Fichier JSON `results/ad-hoc_results.json` avec toutes les métriques

### 3. Valider une Solution

```bash
# Valider une solution spécifique
python validator.py -i instances/bronze/bronze_easy_01.txt \
                    -o results/ad-hoc/bronze/bronze_easy_01.out \
                    -v
```

**Vérifications effectuées :**
- Format de sortie (SAT/UNSAT)
- Tous les colis placés
- Dimensions correctes (rotations autorisées)
- Pas de dépassement du véhicule
- Pas de chevauchement entre colis
- Dimensions positives

### 4. Comparer les Solveurs

```bash
# Comparer deux solveurs (ad-hoc vs futur générique)
python compare_solvers.py results/ad-hoc_results.json \
                         results/generic_results.json

# Comparer sur une league spécifique
python compare_solvers.py results/ad-hoc_results.json \
                         results/generic_results.json \
                         --leagues gold

# Générer un rapport JSON
python compare_solvers.py results/*.json --output benchmarks/comparison.json
```

## Indicateurs de Comparaison

### Indicateurs Primaires

1. **Taux de succès** : Pourcentage de solutions valides
   - *Justification* : Mesure la robustesse du solveur
   - *Aide à la décision* : Solveur fiable vs rapide mais instable

2. **Nombre de véhicules** : Moyenne sur les instances SAT
   - *Justification* : Objectif principal du problème
   - *Aide à la décision* : Qualité de la solution

3. **Temps d'exécution** : Moyenne et médiane
   - *Justification* : Contrainte pratique (compétition, production)
   - *Aide à la décision* : Compromis qualité/temps

### Indicateurs Secondaires

4. **Taux SAT/UNSAT** : Combien d'instances sont résolubles
   - *Justification* : Détecte les limitations du solveur
   
5. **Timeouts** : Instances non terminées dans le temps imparti
   - *Justification* : Identifie les cas difficiles
   
6. **Temps médian** : Moins sensible aux outliers que la moyenne
   - *Justification* : Performance typique

## Caractéristiques des Instances

### Types d'instances

| Type | Description | But |
|------|-------------|-----|
| **easy** | Colis petits, véhicule grand | Validation de base |
| **standard** | Ratio colis/véhicule réaliste | Performance générale |
| **dense** | Gros colis, peu d'espace | Cas difficile |
| **sparse** | Petits colis, beaucoup d'espace | Cas facile, test de scalabilité |
| **elongated** | Colis avec 1 dimension grande | Test des heuristiques |
| **flat** | Colis plats (faible hauteur) | Test empilement |
| **mixed** | Colis de tailles très variées | Réaliste |
| **small_truck** | Véhicule petit | Contrainte forte |
| **large_truck** | Véhicule grand | Facilite le placement |
| **timed** | Avec contraintes de temps (Gold) | Fonctionnalité avancée |
| **extreme** | Cas limites | Test robustesse |
| **scalability** | Grandes instances | Performance N→1000 |

### Passage à l'Échelle

```
Bronze:   10 colis  →  Validation rapide, cas de base
Silver:  100 colis  →  Performance intermédiaire
Gold:   1000 colis  →  Scalabilité, cas réels

Temps attendus:
  Bronze:  < 1s
  Silver:  < 10s
  Gold:    < 300s (5 minutes)
```

## Exemple de Workflow Complet

```bash
# 1. Générer les instances
python generate_instances.py --generate

# 2. Tester le solveur ad-hoc
python run_tests.py --solver ../ad-hoc/run.py --name ad-hoc -v

# 3. (Plus tard) Tester le solveur générique
python run_tests.py --solver ../generic/solve.py --name generic -v

# 4. Comparer les résultats
python compare_solvers.py results/ad-hoc_results.json \
                         results/generic_results.json \
                         --output benchmarks/comparison_report.json

# 5. Analyser les résultats
cat benchmarks/comparison_report.json
```

## Format des Fichiers

### Instance (entrée)
```
L W H           # Dimensions du véhicule
N               # Nombre de colis
L1 W1 H1 D1     # Pour chaque colis: dimensions + délai
L2 W2 H2 D2
...
```

### Solution (sortie)
```
SAT                           # ou UNSAT
V X1 Y1 Z1 X2 Y2 Z2          # Pour chaque colis
V X1 Y1 Z1 X2 Y2 Z2
...
```
- `V`: ID du véhicule (0-indexed)
- `(X1,Y1,Z1)`: Coin inférieur gauche avant
- `(X2,Y2,Z2)`: Coin supérieur droit arrière

### Métadonnées (JSON)
```json
{
  "name": "bronze_easy_01",
  "league": "bronze",
  "seed": 42,
  "file": "instances/bronze/bronze_easy_01.txt",
  "max_truck_dims": "400x210x220",
  "max_item_dims": "500x500x500"
}
```

### Résultats (JSON)
```json
[
  {
    "instance": "bronze_easy_01",
    "league": "bronze",
    "solver": "ad-hoc",
    "status": "SAT",
    "valid": true,
    "nb_vehicles": 1,
    "execution_time": 0.023,
    "error_message": null
  }
]
```