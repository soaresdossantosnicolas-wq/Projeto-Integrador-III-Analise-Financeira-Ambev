#!/usr/bin/env bash
# Interrompe a preparação se qualquer instalação falhar.
set -euo pipefail
if [ -f packages.txt ]; then
    sudo apt-get update
    sudo xargs -r apt-get install -y < packages.txt
fi
python -m pip install -r requirements-dev.txt
python -m pip check
echo 'Dependências instaladas e verificadas.'
