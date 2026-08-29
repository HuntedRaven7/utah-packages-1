set shell := ["bash", "-euo", "pipefail", "-c"]

validate:
    python3 tools/validate.py

show-package-set:
    sed -e '/^#/d' -e '/^$/d' config/bootstrap-packages.txt
