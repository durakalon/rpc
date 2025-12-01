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
  - Propriétés : `volume`, `base_area`, `dimensions`, `longest_side`
  - **Nouveau** : Orientations précomputées (6 permutations, dédupliquées)
  - Méthodes : `filter_orientations(vehicle)` pour filtrage optimisé

- **`Vehicle`** : Représente un véhicule
  - Propriétés : dimensions, volume
  
- **`Placement`** : Représente le placement d'un colis dans un véhicule
  - Méthodes : `overlaps_with()` pour détection de chevauchement
  
- **`VehiclePacker`** : Gère le remplissage d'un véhicule unique
  - Algorithme de placement : Bottom-Left-Back amélioré
  - **Nouveau** : Support des zones de livraison (x_min, x_max)
  - **Nouveau** : `try_add_item_with_score()` pour Best-Fit
  - **Nouveau** : `remove_item()` pour redistribution
  - Détection de collisions optimisée
  - Déduplication des positions candidates

#### 2. **Algorithme Principal** (`BinPackingSolver`)

**Approche : Best Fit Decreasing (BFD) + Local Search**

```
Phase 1 - Construction initiale :
  Pour chaque colis (trié par contrainte de livraison + heuristique) :
    1. Calculer le score pour chaque véhicule existant
    2. Choisir le véhicule avec le meilleur score (utilisation maximale)
    3. Si aucun ne convient, créer un nouveau véhicule
    4. Appliquer les contraintes de zone de livraison si applicable

Phase 2 - Optimisation locale (Local Search) :
  Répéter jusqu'à convergence (max 10 itérations) :
    1. Identifier le véhicule le moins rempli
    2. Tenter de redistribuer ses colis dans les autres véhicules
    3. Si réussi, supprimer ce véhicule
    4. Renuméroter les véhicules restants
```

**Stratégie de placement (Bottom-Left-Back améliorée) :**
- Génère des positions candidates (set dédupliqué)
- Filtre par zones de livraison si applicable
- Trie par priorité : z croissant, puis y, puis x
- Teste les orientations précomputées et filtrées
- Vérifie l'absence de chevauchement et de dépassement

#### 3. **Contraintes de Livraison (League Gold)**

**Gestion des contraintes d'ordre :**
- Groupement des colis par temps de livraison (D)
- Allocation de zones spatiales le long de l'axe x (longueur du camion)
- Principe : colis livrés en premier (D plus petit) → zones arrière (x plus grand)
- Colis non contraints (D=-1) peuvent utiliser tout l'espace

**Calcul des zones :**
- Allocation proportionnelle au volume de chaque groupe de livraison
- Zones contigües pour éviter la fragmentation
- Respect automatique dans les méthodes de placement

#### 4. **Heuristiques de Tri**

Quatre heuristiques implémentées avec support des contraintes de livraison :

1. **`VOLUME_DECREASING`** (défaut)
   - Clé primaire : temps de livraison (D croissant)
   - Clé secondaire : volume décroissant
   - Meilleure pour maximiser l'utilisation

2. **`LONGEST_SIDE_DECREASING`**
   - Clé primaire : temps de livraison (D croissant)
   - Clé secondaire : dimension maximale décroissante
   - Utile pour les colis allongés

3. **`AREA_DECREASING`**
   - Clé primaire : temps de livraison (D croissant)
   - Clé secondaire : surface de base décroissante
   - Bon pour les colis plats

4. **`HEIGHT_DECREASING`**
   - Clé primaire : temps de livraison (D croissant)
   - Clé secondaire : hauteur décroissante
   - Optimise l'empilement vertical

**Note** : Les colis contraints (D ≥ 0) sont toujours traités avant les non-contraints (D = -1)

#### 5. **Validation de Solution**

**Nouveau** : Fonction `validate_solution()` qui vérifie :
- Respect des dimensions du véhicule (aucun dépassement)
- Absence de chevauchement entre colis
- Vérification basique des contraintes d'ordre de livraison
- Rapports détaillés en mode verbose

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

**Phase de construction :**
- **Tri** : O(N log N) où N = nombre de colis
- **Placement par colis** : O(V × N × P × O × C)
  - V : nombre de véhicules (≤ N)
  - P : nombre de colis déjà placés par véhicule (≤ N)
  - O : orientations valides (≤ 6, précomputées)
  - C : positions candidates dédupliquées (≤ 3P + 1)
- **Best-Fit** : O(V) comparaisons par colis

**Phase d'optimisation locale :**
- **Itérations** : O(V) maximum (10 itérations max)
- **Par itération** : O(P × V) pour redistribuer les colis

**Total** : O(N² × V × P) dans le pire cas, mais linéaire en pratique

### Complexité Spatiale

- **Items et orientations** : O(N) 
- **Véhicules et placements** : O(V × P)
- **Zones de livraison** : O(D) où D = nombre de temps de livraison distincts
- **Positions candidates** : O(P) par recherche (set dédupliqué)

**Total** : O(N + V × P) ≈ O(N) en pratique

### Optimisations Implémentées

1. **Orientations précomputées** : 
   - Calcul unique par item à l'initialisation
   - Déduplication automatique (cubes, etc.)
   - Filtrage par véhicule pour éviter tests inutiles

2. **Best-Fit** : 
   - Meilleure utilisation des véhicules
   - Réduction du nombre total de véhicules
   - Score sans modification d'état (efficace)

3. **Déduplication des candidats** : 
   - Utilisation de sets pour éliminer positions identiques
   - Filtrage précoce des positions hors-zone

4. **Local Search** : 
   - Post-optimisation pour réduire le nombre de véhicules
   - Convergence rapide (généralement 2-3 itérations)
   - Arrêt automatique si aucune amélioration

5. **Zones de livraison** : 
   - Calcul unique au début
   - Application directe lors du placement
   - Pas de rétroaction nécessaire

6. **Early termination** : 
   - Arrêt dès qu'une position valide est trouvée
   - Vérification volumétrique avant test géométrique


## Fichiers Importants

- **`solver.py`** : Implémentation du solveur (classes et algorithmes)
- **`run.py`** : Script d'exécution avec CLI
- **`README.md`** : Ce fichier
- **`../testsuite/`** : Suite de tests et validation