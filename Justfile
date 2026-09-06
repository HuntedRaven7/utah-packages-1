set shell := ["bash", "-euo", "pipefail", "-c"]

validate:
    python3 tools/validate.py
