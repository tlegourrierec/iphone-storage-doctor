# Mettre le projet sur GitHub, pas à pas

## Ce que tu uploades exactement

**Tout le dossier `~/Downloads/iphone-storage-doctor`, sauf ce que `.gitignore`
exclut déjà.** Git s'en occupe : tu n'as rien à trier à la main. Concrètement,
34 fichiers partent :

| Ce qui monte | Pourquoi |
|---|---|
| `ipsd/` (13 fichiers) | Le code |
| `tests/` (8 fichiers) | Les tests — c'est ce qui donne confiance |
| `README.md`, `README.fr.md` | La vitrine |
| `CONTRIBUTING.md`, `LICENSE` | Les règles du jeu |
| `Formula/` | La formule Homebrew |
| `.github/` | CI et gabarits d'issues |
| `docs/`, `pyproject.toml`, `install.sh` | Doc et packaging |

| Ce qui NE monte PAS | Pourquoi |
|---|---|
| `.venv/`, `build/`, `*.egg-info/` | Artefacts locaux, régénérés |
| `~/iphone-storage-doctor/quarantine/` | **Tes fichiers personnels** — hors du repo, jamais versionnés |
| `~/iphone-storage-doctor/snapshots/` | Contient ton UDID et tes apps |

> Vérifie avant de pousser : `git ls-files | wc -l` doit afficher **34**, et
> `git status --short` doit être vide.

## Étape 1 — Remplacer le pseudo GitHub

Deux fichiers contiennent `OWNER` :

```bash
cd ~/Downloads/iphone-storage-doctor
sed -i '' 's/OWNER/TON_PSEUDO/g' README.md Formula/iphone-storage-doctor.rb
git add -A && git commit -m "Point URLs at the public repository"
```

## Étape 2 — Créer le dépôt et pousser

Avec la CLI GitHub (une seule commande) :

```bash
gh repo create iphone-storage-doctor --public --source=. --push
```

Sans la CLI : crée le dépôt sur github.com (vide, sans README), puis

```bash
git remote add origin https://github.com/TON_PSEUDO/iphone-storage-doctor.git
git branch -M main
git push -u origin main
```

## Étape 3 — Les topics, le levier le plus rentable

Sur la page du dépôt, roue dentée **About** > Topics. GitHub les indexe et les
expose dans ses pages de navigation. C'est gratuit et c'est le premier facteur
de découverte :

```
ios  iphone  storage  disk-usage  battery-health  cli  macos
usb  libimobiledevice  pymobiledevice3  device-management
```

Dans le même panneau, la description — en anglais, avec les mots que les gens
tapent vraiment :

> Diagnose iPhone storage and battery health over USB — find what's eating
> space, and why an old iPhone feels slow.

## Étape 4 — Une release, pour que Homebrew marche

```bash
git tag v1.2.0 && git push origin v1.2.0
gh release create v1.2.0 --generate-notes
```

Récupère l'empreinte de l'archive et mets-la dans la formule :

```bash
curl -sL https://github.com/TON_PSEUDO/iphone-storage-doctor/archive/refs/tags/v1.2.0.tar.gz | shasum -a 256
```

Colle le résultat à la place de `REPLACE_WITH_RELEASE_TARBALL_SHA256`, commit,
push.

## Étape 5 — Le tap Homebrew

Un tap est un dépôt **séparé**, obligatoirement nommé `homebrew-tap` :

```bash
cd ~ && gh repo create homebrew-tap --public --clone
mkdir -p homebrew-tap/Formula
cp ~/Downloads/iphone-storage-doctor/Formula/iphone-storage-doctor.rb homebrew-tap/Formula/
cd homebrew-tap && git add -A && git commit -m "Add iphone-storage-doctor" && git push
```

Les utilisateurs installent alors en deux lignes :

```bash
brew tap TON_PSEUDO/tap
brew install iphone-storage-doctor
```

## Étape 6 — Mettre le projet en avant

**L'angle, d'abord.** Ne te positionne pas comme « iPhone cleaner » : il y en a
cinquante, tous interchangeables. Positionne-toi sur ce que tu es seul à dire :

> Votre iPhone n'est pas lent à cause de vos fichiers. Il est lent parce que sa
> batterie est usée — et voici comment le mesurer.

C'est vrai, c'est vérifiable en trente secondes, et ça contredit toute la
catégorie. C'est ce qui fait cliquer.

Par ordre de rendement réel :

1. **`awesome-ios` et `awesome-macos-command-line`** — une pull request d'une
   ligne. C'est la source de trafic la plus durable, et elle ne s'épuise pas.
2. **Le dépôt `pymobiledevice3`** — ouvre une discussion présentant un projet
   bâti dessus. Public exactement ciblé, accueil généralement bon.
3. **Reddit** : r/iphone, r/commandline, r/macapps. Insiste sur ce que l'outil
   **refuse** de promettre — ces communautés détestent le marketing et
   récompensent l'honnêteté technique.
4. **Hacker News** — une seule tentative, un mardi matin heure de New York.
   Titre suggéré : *"Show HN: Your old iPhone isn't slow because of storage"*.

**Ce qui fait rester les gens sur la page** : le bloc de sortie console en tête
de README (le verdict batterie, pas une liste de fonctions), et le tableau
« what it cannot do » avec les trois refus testés. Ce tableau est
contre-intuitif — il rassure plus qu'il n'inquiète, parce qu'il prouve que tu
as vraiment sondé l'appareil.

## Étape 7 — Avant d'annoncer largement

Les messages de la CLI sont en **français**. Le README anglais suffit pour être
trouvé, mais un anglophone qui installe verra une sortie qu'il ne comprend pas
et partira. C'est le principal frein hors francophonie : prévoir une passe
d'internationalisation (extraire les chaînes, `--lang en`) avant les étapes 6.3
et 6.4.
