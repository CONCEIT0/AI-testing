# IA Portátil (Python + Ollama)

Este projeto cria uma IA local (estilo chat) para usar no seu pendrive, com:

- Chat estilo ChatGPT no terminal
- Base de conhecimento com seus textos (RAG local)
- Suporte a imagens na pergunta (modelo multimodal)
- Instalação simples para Linux/macOS e Windows

## 1) Instalação rápida

### Linux/macOS
```bash
./setup_portable.sh
```

### Windows
Execute:
```bat
setup_portable.bat
```

## 2) Instalar e preparar Ollama

Instale o Ollama: https://ollama.com/download

Depois baixe os modelos (uma vez):
```bash
ollama pull llama3.1:8b
ollama pull llava:7b
ollama pull mxbai-embed-large
```

## 3) Uso

Ative o ambiente virtual:

- Linux/macOS:
```bash
source .venv/bin/activate
```

- Windows:
```bat
.venv\Scripts\activate
```

Crie config padrão:
```bash
python src/ia_pendrive.py init
```

Indexe seus textos:
```bash
python src/ia_pendrive.py ingest ./meus_textos
```

Converse:
```bash
python src/ia_pendrive.py chat
```

## Comandos dentro do chat

- `/imagem CAMINHO_DA_IMAGEM` → usa imagem na próxima pergunta
- `/limparimagem` → remove imagem ativa
- `/sair` → encerra
- `/pasta` → mostra a pasta atual que o programa está usando

## Estrutura

- `src/ia_pendrive.py`: app principal
- `data/config.json`: configuração dos modelos/host
- `data/chunks.jsonl`: base vetorial local

## Observações para pendrive

- Você pode levar esta pasta inteira no pendrive.
- Em cada computador, rode o instalador (`setup_portable.sh` ou `.bat`).
- Os modelos do Ollama ocupam bastante espaço. Se quiser mobilidade total, mantenha os modelos no próprio computador alvo ou num SSD externo com espaço.


## Erro comum: "caminho não achado"

Se aparecer "caminho não encontrado":

1. Rode `/pasta` dentro do chat para ver a pasta atual.
2. Use caminho absoluto do arquivo/pasta (ex.: `E:\meus_textos` no Windows).
3. Para imagens, teste:
   - `/imagem E:\fotos\img1.jpg` (Windows)
   - `/imagem /media/usb/fotos/img1.jpg` (Linux)
4. No comando de ingestão, também pode usar absoluto:
```bash
python src/ia_pendrive.py ingest /caminho/completo/para/meus_textos
```

O programa agora mostra a pasta atual (`cwd`) quando não encontra o caminho, para facilitar.
