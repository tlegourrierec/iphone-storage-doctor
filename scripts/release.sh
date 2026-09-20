#!/usr/bin/env bash
# Publie une version et met la formule Homebrew en état de marche.
#
# La formule ne peut fonctionner qu'une fois l'archive publiée : son sha256
# porte sur le tarball que GitHub génère pour le tag. Ce script fait les deux
# dans le bon ordre, puis met le tap à jour.
#
#   ./scripts/release.sh 1.3.0
set -euo pipefail

version="${1:?usage: ./scripts/release.sh <version>}"
owner="$(gh api user --jq .login)"
repo="iphone-storage-doctor"
tap_repo="homebrew-tap"
formula="Formula/iphone-storage-doctor.rb"
red() { printf '\033[31m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }

[[ -z "$(git status --porcelain)" ]] || { red "Working tree is dirty. Commit first."; exit 1; }

# 1. Le tag et la release. GitHub fabrique l'archive à ce moment-là.
if ! git rev-parse "v$version" >/dev/null 2>&1; then
  git tag "v$version"
fi
git push origin main --tags
gh release view "v$version" >/dev/null 2>&1 || gh release create "v$version" --generate-notes

# 2. L'empreinte de l'archive publiée. On attend qu'elle soit servie.
url="https://github.com/$owner/$repo/archive/refs/tags/v$version.tar.gz"
echo "-> Waiting for GitHub to serve $url"
for _ in $(seq 1 15); do
  if curl -sfL "$url" -o /tmp/ipsd-release.tar.gz; then break; fi
  sleep 2
done
[[ -s /tmp/ipsd-release.tar.gz ]] || { red "Archive not available yet. Retry in a minute."; exit 1; }
sha="$(shasum -a 256 /tmp/ipsd-release.tar.gz | cut -d' ' -f1)"
green "sha256 = $sha"

# 3. La formule, renseignée avec l'URL et l'empreinte réelles.
/usr/bin/sed -i '' \
  -e "s|url \".*\"|url \"$url\"|" \
  -e "s|sha256 \".*\"|sha256 \"$sha\"|" \
  -e "s|version \".*\"|version \"$version\"|" \
  "$formula"
git add "$formula" && git commit -m "Formula: point at v$version" && git push origin main

# 4. Le tap, dépôt séparé qu'Homebrew exige.
workdir="$(mktemp -d)"
if gh repo view "$owner/$tap_repo" >/dev/null 2>&1; then
  gh repo clone "$owner/$tap_repo" "$workdir/tap" -- -q
else
  gh repo create "$owner/$tap_repo" --public \
    --description "Homebrew formulae by $owner" >/dev/null
  git init -q "$workdir/tap"
  git -C "$workdir/tap" remote add origin "https://github.com/$owner/$tap_repo.git"
  git -C "$workdir/tap" branch -M main
fi
mkdir -p "$workdir/tap/Formula"
cp "$formula" "$workdir/tap/Formula/"
git -C "$workdir/tap" add -A
git -C "$workdir/tap" commit -q -m "iphone-storage-doctor $version" || true
git -C "$workdir/tap" push -q -u origin main

green "Released v$version. Anyone can now install it with:"
echo "    brew tap $owner/tap"
echo "    brew install iphone-storage-doctor"
