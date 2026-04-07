#!/usr/bin/env bash
# --venv: pytest corre en un venv aislado (solo deps de ansible-test/units.txt), sin pytest-ansible de la imagen.
set -euo pipefail
exec ansible-test units --venv "$@"
