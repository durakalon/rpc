# Projet RPC

## Description

Vous êtes responsable de la logistique au Service d′Acheminement National dédié au Trans-
port d′Articles de la Compagnie Logistique Aérienne Ultra Spéciale. Vous disposez de plusieurs
véhicules spécialisés (Technologies de Roulage Avancées, Innovantes et Novatrices pour En-
gins Autonomes Urbains) de capacités différentes et d′une liste d′articles à livrer à différentes
adresses. Votre objectif est d′optimiser la répartition des colis dans les véhicules pour minimiser
le nombre de véhicules utilisés tout en respectant les capacités de charge maximale de chaque
véhicules.

La description complète du projet est disponible en pdf `Projet RPC.pdf`

## Outils

Ce répertoire contient les outils suivants :
- `generate.py` : générateur de données d'entrée
- `visualize.py` : visualisateur de données de sortie
- `ad-hoc/` : solveur ad-hoc basé sur l'algorithme First Fit Decreasing

### `generate.py`

Permet de gérénérer des données d'entrée pour le projet pour les trois leagues (bronze, silver et gold).

Utiliser la commande :

```bash
python3 generate.py --help
```

Pour voir comment l’utiliser.

### `visualize.py`

Permet de visualiser les données de sortie du projet.

Utiliser la commande :

```bash
python3 visualize.py --help
```

Pour voir comment l'utiliser.

### `ad-hoc/`

Solveur ad-hoc pour le problème de bin packing 3D. Utilise l'algorithme First Fit Decreasing avec plusieurs heuristiques de tri.

**Utilisation rapide :**

```bash
# Résoudre depuis stdin
python ad-hoc/run.py < input.sample > output.txt

# Résoudre depuis un fichier
python ad-hoc/run.py -i input.sample -o output.txt

# Mode verbeux avec statistiques
python ad-hoc/run.py -i input.sample -v

# Trouver automatiquement la meilleure heuristique
python ad-hoc/run.py -i input.sample --best -v
```
