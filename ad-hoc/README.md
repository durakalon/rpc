# Solveur Ad-Hoc

## Description du Problème

Ce solveur résout le problème d'optimisation logistique suivant :

**Données d'entrée :**
- **Véhicule** : Un type de véhicule avec dimensions fixes (L × W × H)
- **Colis** : N colis, chacun avec :
  - Dimensions (L × W × H)
  - Temps de livraison D (optionnel, -1 si non contraint)

**Contraintes :**
1. Chaque colis doit être placé dans un véhicule
2. Les colis ne peuvent pas dépasser les dimensions du véhicule
3. Les colis ne peuvent pas se chevaucher
4. Les colis peuvent être tournés (6 orientations possibles)
5. Contraintes d'ordre de livraison (league Gold uniquement)

**Objectif :**
Minimiser le nombre de véhicules utilisés pour transporter tous les colis.

## Format des Données

### Format d'entrée
```
L W H           # Dimensions du véhicule
N               # Nombre de colis
L1 W1 H1 D1     # Dimensions et délai du colis 1
L2 W2 H2 D2     # Dimensions et délai du colis 2
...
LN WN HN DN     # Dimensions et délai du colis N
```

### Format de sortie
```
SAT             # ou UNSAT si impossible
V X1 Y1 Z1 X2 Y2 Z2    # Pour chaque colis (V = ID véhicule, coordonnées du coin opposé)
...
```

Exemple :
```
0 0 0 0 40 20 10      # Colis 0 dans véhicule 0, de (0,0,0) à (40,20,10)
0 0 20 0 40 30 10     # Colis 1 dans véhicule 0, de (0,20,0) à (40,30,10)
```

## Architecture du Solveur

### Composants Principaux

#### 1. **Classes de Données** (`solver.py`)

- **`Item`** : Représente un colis avec dimensions et contraintes
  - Propriétés : `volume`, `base_area`, `dimensions`
  - Méthodes : calcul automatique des métriques

- **`Vehicle`** : Représente un véhicule
  - Propriétés : dimensions, volume
  
- **`Placement`** : Représente le placement d'un colis dans un véhicule
  - Méthodes : `overlaps_with()` pour détection de chevauchement
  
- **`VehiclePacker`** : Gère le remplissage d'un véhicule unique
  - Algorithme de placement : Bottom-Left-Back
  - Détection de collisions
  - Gestion de toutes les orientations possibles

#### 2. **Algorithme Principal** (`BinPackingSolver`)

**Approche : First Fit Decreasing (FFD) avec variantes**

```
Pour chaque colis (dans l'ordre du tri) :
    1. Essayer de placer dans un véhicule existant
    2. Si impossible, créer un nouveau véhicule
    3. Si ne rentre nulle part, marquer comme non placé
```

**Stratégie de placement (Bottom-Left-Back) :**
- Génère des positions candidates (coins des colis existants + origine)
- Trie par priorité : z croissant, puis y, puis x
- Teste toutes les orientations du colis
- Vérifie l'absence de chevauchement et de dépassement

#### 3. **Heuristiques de Tri**

Quatre heuristiques implémentées :

1. **`VOLUME_DECREASING`** (défaut)
   - Trie par volume décroissant
   - Meilleure pour maximiser l'utilisation

2. **`LONGEST_SIDE_DECREASING`**
   - Trie par dimension maximale décroissante
   - Utile pour les colis allongés

3. **`AREA_DECREASING`**
   - Trie par surface de base décroissante
   - Bon pour les colis plats

4. **`HEIGHT_DECREASING`**
   - Trie par hauteur décroissante
   - Optimise l'empilement vertical

## Utilisation

### Installation

Aucune dépendance externe requise. Python 3.7+ uniquement.

```bash
cd ad-hoc
```

### Exécution Basique

```bash
# Depuis stdin/stdout
python run.py < ../input.sample > output.txt

# Depuis fichiers
python run.py -i ../input.sample -o output.txt
```

### Options Avancées

```bash
# Choisir une heuristique spécifique
python run.py -i input.txt --heuristic volume
python run.py -i input.txt --heuristic longest_side
python run.py -i input.txt --heuristic area
python run.py -i input.txt --heuristic height

# Trouver automatiquement la meilleure heuristique
python run.py -i input.txt --best -o output.txt

# Mode verbeux (statistiques sur stderr)
python run.py -i input.txt -v

# Combinaison
python run.py -i input.txt --best -v -o output.txt
```

## Complexité

### Complexité Temporelle

- **Tri** : O(N log N) où N = nombre de colis
- **Placement par colis** : O(N × P × O × C)
  - P : nombre de colis déjà placés (≤ N)
  - O : orientations testées (≤ 6)
  - C : positions candidates (≤ 3P + 1)
- **Total** : O(N² × P) dans le pire cas

### Complexité Spatiale

- O(N) pour stocker les colis et placements
- O(V × P) pour les véhicules et leurs placements

### Optimisations Implémentées

1. **Tri préalable** : Réduit les tentatives infructueuses
2. **Bottom-Left-Back** : Positions candidates limitées
3. **Early termination** : Arrêt dès qu'une position valide est trouvée
4. **Vérification volumétrique** : Évite les essais impossibles