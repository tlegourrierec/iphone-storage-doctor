#!/usr/bin/env bash
# Installation sans Homebrew. Vérifie l'environnement avant d'agir, parce
# qu'un message clair vaut mieux qu'un échec de pip au milieu d'une trace.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
red() { printf '\033[31m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  red "This tool talks to an iPhone over USB and is tested on macOS only."
  red "On Linux you also need usbmuxd running. Continuing anyway."
fi

# macOS livre Python 3.9 ; le projet demande 3.11+. pipx règle le problème en
# utilisant son propre interpréteur, à condition qu'il soit assez récent.
if ! command -v pipx >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "-> Installing pipx via Homebrew..."
    brew install pipx
    pipx ensurepath
  else
    red "pipx is required and Homebrew was not found."
    red "Install Homebrew from https://brew.sh, then run this script again."
    exit 1
  fi
fi

python_bin="$(pipx environment --value PIPX_DEFAULT_PYTHON 2>/dev/null || echo python3)"
version="$("$python_bin" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
major="${version%%.*}"; minor="${version##*.}"
if (( major < 3 || (major == 3 && minor < 11) )); then
  red "pipx would use Python $version, but this project needs 3.11 or newer."
  red "Fix it with:  brew install python@3.13 && pipx reinstall-all --python \$(brew --prefix)/bin/python3.13"
  exit 1
fi

echo "-> Installing iphone-storage-doctor (Python $version)..."
pipx install --force "$here"

echo
green "Done. Plug in the iPhone, unlock it, tap \"Trust This Computer\", then run:"
echo "    ipsd doctor"
echo
echo "If 'ipsd' is not found, run 'pipx ensurepath' and open a new terminal."
