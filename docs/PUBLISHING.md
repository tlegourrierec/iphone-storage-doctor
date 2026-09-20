# Publier et rendre le projet trouvable

## 1. Créer le dépôt

```bash
cd ~/Downloads/iphone-storage-doctor
gh repo create iphone-storage-doctor --public --source=. --push
```

Sans la CLI GitHub : créer le dépôt sur github.com, puis

```bash
git remote add origin https://github.com/TON_PSEUDO/iphone-storage-doctor.git
git push -u origin main
```

**Avant de pousser**, remplacer `OWNER` par ton pseudo GitHub dans
`README.md` et `Formula/iphone-storage-doctor.rb` :

```bash
sed -i '' 's/OWNER/TON_PSEUDO/g' README.md Formula/iphone-storage-doctor.rb
```

## 2. Les topics — le levier le plus rentable

GitHub indexe les topics et les expose dans ses pages de navigation. C'est le
premier facteur de découverte, et il est gratuit. Sur la page du dépôt,
roue dentée « About » > Topics :

```
ios  iphone  storage  disk-usage  battery-health  cli  macos
usb  libimobiledevice  pymobiledevice3  cleaner  device-management
```

Mettre aussi une description d'une ligne, en anglais, qui contient les mots que
les gens tapent réellement :

> Diagnose iPhone storage and battery health over USB — find what's eating
> space and why an old iPhone feels slow.

## 3. Ce qui fait la différence dans les résultats de recherche

- **Le README en anglais.** C'est 90 % de la découvrabilité. La version
  française reste en `README.fr.md`, liée en haut.
- **Le bloc de sortie console dès les premières lignes.** Les gens décident en
  trois secondes. Montrer le verdict batterie, pas une liste de fonctions.
- **Un angle qui n'existe pas ailleurs.** Les dépôts « iphone cleaner »
  promettent tous la même chose. Celui-ci mesure la santé batterie et dit
  qu'aucun nettoyage ne rend de la vitesse. C'est ça qu'il faut mettre en
  titre, pas « storage analyzer ».
- **Les limites documentées.** Le tableau « what it cannot do » est ce qui fait
  qu'un développeur fait confiance au reste.

## 4. Une release, pour que Homebrew fonctionne

```bash
git tag v1.1.0 && git push origin v1.1.0
gh release create v1.1.0 --generate-notes
```

Puis récupérer l'empreinte de l'archive et la mettre dans la formule :

```bash
curl -sL https://github.com/TON_PSEUDO/iphone-storage-doctor/archive/refs/tags/v1.1.0.tar.gz | shasum -a 256
```

## 5. Le tap Homebrew

Un tap est un dépôt séparé **obligatoirement** nommé `homebrew-tap` :

```bash
gh repo create homebrew-tap --public
mkdir -p homebrew-tap/Formula
cp Formula/iphone-storage-doctor.rb homebrew-tap/Formula/
```

Les utilisateurs installent alors avec :

```bash
brew tap TON_PSEUDO/tap
brew install iphone-storage-doctor
```

## 6. Où l'annoncer

Par ordre de rendement réel :

1. **`awesome-ios`** et **`awesome-macos-command-line`** — une pull request
   ajoutant une ligne. C'est la source de trafic la plus durable.
2. **Le dépôt `pymobiledevice3`** — ouvrir une discussion présentant un projet
   construit dessus. Le public y est exactement le bon.
3. **r/jailbreak, r/iphone, r/commandline** — en insistant sur ce que l'outil
   refuse de promettre. C'est ce qui passe bien dans ces communautés.
4. **Hacker News** — l'angle « aucun nettoyeur ne vous dira que c'est la
   batterie » est un titre qui tient. Une seule tentative, un mardi matin
   heure de New York.

## 7. Ce qui reste à faire pour un public international

Les messages de la CLI sont en français. Le README est en anglais, ce qui suffit
pour être trouvé, mais un utilisateur anglophone verra une sortie française.
C'est le principal frein à l'adoption hors francophonie : prévoir une passe
d'internationalisation (extraire les chaînes, ajouter `--lang en`) avant
d'annoncer largement.
