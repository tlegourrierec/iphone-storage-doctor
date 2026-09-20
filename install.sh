#!/usr/bin/env bash
# Installation sans Homebrew, via pipx (plus rapide et isolé).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v pipx >/dev/null 2>&1; then
  echo "→ Installation de pipx…"
  brew install pipx
  pipx ensurepath
fi

echo "→ Installation de iphone-storage-doctor…"
pipx install --force "$here"

echo
echo "✓ Terminé. Branche l'iPhone, déverrouille-le, puis lance :"
echo "    ipsd doctor"
