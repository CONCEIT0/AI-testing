#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat <<MSG

Instalação concluída.

Próximos passos:
1) Instale o Ollama: https://ollama.com/download
2) Baixe os modelos:
   ollama pull llama3.1:8b
   ollama pull llava:7b
   ollama pull mxbai-embed-large
3) Inicialize:
   source .venv/bin/activate
   python src/ia_pendrive.py init
4) Indexe seus textos:
   python src/ia_pendrive.py ingest ./meus_textos
5) Converse:
   python src/ia_pendrive.py chat

MSG
