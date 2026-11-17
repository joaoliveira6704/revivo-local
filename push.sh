#!/bin/sh
# Envia alterações do WordPress local para o site real. Ver: ./push.sh help
cd "$(dirname "$0")" && exec python3 -I tools/push.py "$@"
