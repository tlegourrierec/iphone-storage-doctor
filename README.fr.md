# iphone-storage-doctor

Analyse le stockage d'un iPhone **branché en USB** depuis un Mac, explique où part
la place, et récupère ce qui est récupérable — sans jailbreak, sans application à
installer sur le téléphone.

```
ipsd doctor
```

## Ce que l'outil fait vraiment

Il n'y a pas de magie possible sur iOS, et cet outil est construit autour de cette
contrainte plutôt qu'en la cachant. Trois sources d'information sont exploitées :

| Source | Ce qu'elle donne | Portée |
|---|---|---|
| `com.apple.disk_usage` | Capacité, occupé, libre immédiat, purgeable | Tout le disque |
| `installation_proxy` | Poids **code + données** de chaque app | Toutes les apps |
| `AFC` | Inventaire fichier par fichier | `/var/mobile/Media` seulement |

La somme des deux dernières ne couvre pas le total : le reste (iOS lui-même, les
caches système, iCloud) est affiché tel quel, sous l'étiquette **« non attribué »**.
L'outil préfère afficher un trou honnête plutôt qu'un camembert inventé.

### Ce que l'outil ne peut pas faire

**Vider le cache d'une app depuis le Mac est impossible.** Les données d'Instagram,
TikTok ou Spotify vivent dans `/var/mobile/Containers/Data/Application/<UUID>/`,
hors de portée d'AFC. Le service `house_arrest` est refusé par iOS pour les apps
de l'App Store (`InstallationLookupFailed`). Aucun logiciel Mac ne contourne ça —
c'est le sandbox iOS, pas une limite d'implémentation.

En revanche l'outil **mesure** ces caches et te dit quoi faire :

| Action | Gain typique |
|---|---|
| Vider le cache depuis les réglages de l'app | partiel |
| Supprimer puis réinstaller l'app | la totalité des données |
| « Décharger l'app » | le binaire seulement — **pas** les données |

C'est ce que fait `ipsd purge` : il chiffre le gain app par app, puis pilote la
désinstallation depuis le Mac. Le binaire se retéléchargera depuis l'App Store.

```bash
ipsd purge --min-data 400     # simulation : qui pèse, et combien on récupère
ipsd purge --app TikTok --apply
```

**Garde-fou.** Désinstaller efface aussi les données locales. L'outil reconnaît
les catégories où c'est irrécupérable — applications d'authentification à deux
facteurs, messageries, portefeuilles crypto, éditeurs photo, prises de notes —
et les **écarte par défaut**, en affichant la raison. `--force-risky` passe
outre, délibérément. En conditions réelles ce filtre a épargné un Microsoft
Authenticator et un Lightroom porteur d'1 Go de projets locaux.

`--apply` exige en plus de taper `SUPPRIMER`, et l'outil mesure l'espace libre
avant/après pour confirmer le gain réel plutôt que l'estimation.

## Installation

### Homebrew

```bash
brew install --formula ./Formula/iphone-storage-doctor.rb
```

### pipx (plus rapide)

```bash
./install.sh
```

## Utilisation

```bash
ipsd devices     # vérifier que l'iPhone est vu
ipsd storage     # compteurs, instantané
ipsd doctor      # diagnostic complet (~2-3 min, parcourt le volume média)
ipsd apps        # classement des apps par espace occupé
ipsd clean       # simulation de nettoyage
ipsd clean --apply --crash   # exécution réelle, après confirmation
ipsd purge       # apps désinstallables, avec le gain chiffré
ipsd plan        # les trois niveaux de nettoyage et leurs gains
ipsd purgeable   # ce qu'iOS appelle « libérable », et pourquoi on n'y touche pas
ipsd trend       # dérive du stockage entre deux instantanés
ipsd restart     # redémarre l'iPhone
```

Toutes les commandes acceptent `--json` pour être branchées sur autre chose.

### Profils de scan

`ipsd doctor --profile fast` ignore les sous-arbres les plus peuplés de la
photothèque. Compte ~30 s au lieu de ~2-3 min, avec un inventaire moins fin.

## Le modèle de sûreté

### Rien n'est supprimé sans ton accord

`--apply` ne vaut pas consentement. Avant de retirer quoi que ce soit de
l'appareil, l'outil affiche exactement ce qu'il a trouvé — combien de fichiers,
quel volume, quelle catégorie — et attend un oui. Hors terminal interactif, il
refuse d'agir plutôt que de supposer un accord ; `--yes` existe pour les
scripts, et doit être tapé délibérément.

Chaque constat porte un niveau, et l'outil ne supprime **que** le premier :

- **SÛR** — cache régénéré par iOS, aucune donnée utilisateur. Supprimé par
  `ipsd clean --apply`, après copie sur le Mac.
- **À ARBITRER** — récupérable, mais c'est un choix : musique hors-ligne,
  podcasts, apps volumineuses. Jamais supprimé automatiquement.
- **MANUEL** — jamais touché. Données utilisateur, ou suppression qui
  corromprait une base iOS.

### La règle qui compte

**Tout ce qui est sous `/DCIM` et `/PhotoData` est classé MANUEL.**

Supprimer une photo via AFC retire le fichier mais laisse son entrée dans
`Photos.sqlite` : bibliothèque incohérente, vignettes fantômes, synchronisation
iCloud qui part en vrille. Les photos se suppriment depuis l'app Photos, et
l'outil refuse de faire autrement — même quand la place à gagner est tentante.

Même logique pour les vignettes `.ithmb` : techniquement supprimables, mais iOS
les reconstruit en chauffant le téléphone pendant des heures, sans gain durable.
Elles sont signalées, pas supprimées.

### Quarantaine

`ipsd clean --apply` copie chaque fichier dans `~/iphone-storage-doctor/quarantine`
**avant** de l'effacer. `--no-quarantine` désactive ce filet, explicitement.

## Performance de l'appareil

Libérer de l'espace n'accélère un iPhone que dans un cas : quand il est proche
de la saturation (sous ~10 % de libre), le système APFS n'a plus de marge et
tout ralentit. Au-delà, passer de 30 à 50 Go libres ne change rien à la vitesse.
`ipsd restart` vide la RAM et les fichiers temporaires — effet réel mais bref.
L'outil ne promet pas mieux.

## Prérequis

- macOS, Python ≥ 3.11
- iPhone branché en USB, déverrouillé, appairé (« Se fier à cet ordinateur »)
- Aucun mode développeur requis

## Développement

```bash
python3 -m venv .venv && ./.venv/bin/pip install -e . pytest
./.venv/bin/python -m pytest tests -q
```

Les tests couvrent les heuristiques sans appareil branché — notamment le
garde-fou qui interdit de classer un fichier `/DCIM` comme supprimable.

## Licence

MIT
