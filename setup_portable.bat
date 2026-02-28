@echo off
setlocal
cd /d %~dp0

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Instalacao concluida.
echo.
echo Proximos passos:
echo 1^) Instale o Ollama: https://ollama.com/download
echo 2^) Baixe os modelos:
echo    ollama pull llama3.1:8b
echo    ollama pull llava:7b
echo    ollama pull mxbai-embed-large
echo 3^) Inicialize:
echo    .venv\Scripts\activate
echo    python src\ia_pendrive.py init
echo 4^) Indexe seus textos:
echo    python src\ia_pendrive.py ingest .\meus_textos
echo 5^) Converse:
echo    python src\ia_pendrive.py chat
