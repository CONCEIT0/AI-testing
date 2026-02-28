#!/usr/bin/env python3
"""
IA portátil em Python (estilo chat) com suporte a:
- Base de conhecimento local (textos)
- Perguntas com contexto recuperado (RAG simples)
- Entrada de imagens (via modelo multimodal no Ollama)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import os
from typing import Any, Dict, List, Optional

import urllib.error
import urllib.request


DEFAULT_DATA_DIR = Path("data")
DEFAULT_STORE = DEFAULT_DATA_DIR / "chunks.jsonl"
DEFAULT_CONFIG = DEFAULT_DATA_DIR / "config.json"

def resolve_input_path(raw: str) -> Path:
    expanded = os.path.expanduser(raw.strip())
    return Path(expanded).resolve()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    denom = na * nb
    if denom == 0:
        return 0.0
    return dot / denom


class OllamaClient:
    def __init__(self, host: str = "http://127.0.0.1:11434") -> None:
        self.host = host.rstrip("/")

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.host}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Erro HTTP {e.code} em {endpoint}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError("Não foi possível conectar ao Ollama. Verifique se ele está instalado e em execução.") from e

    def embed(self, model: str, text: str) -> List[float]:
        data = self._post("/api/embeddings", {"model": model, "prompt": text})
        return data["embedding"]

    def chat(self, model: str, messages: List[Dict[str, Any]], temperature: float = 0.2) -> str:
        data = self._post(
            "/api/chat",
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        return data["message"]["content"]


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


class VectorStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.items: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        self.items = []
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.items.append(json.loads(line))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for item in self.items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def add(self, source: str, chunk: str, emb: List[float]) -> None:
        chunk_id = hashlib.sha1(f"{source}:{chunk}".encode("utf-8")).hexdigest()
        if any(i["id"] == chunk_id for i in self.items):
            return
        self.items.append({"id": chunk_id, "source": source, "text": chunk, "embedding": emb})

    def search(self, query_emb: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        scored: List[tuple[float, Dict[str, Any]]] = []
        for item in self.items:
            score = cosine_similarity(query_emb, item["embedding"])
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored[:top_k] if score > 0.15]

    def persist(self) -> None:
        self._save()


def load_config(path: Path) -> Dict[str, Any]:
    default = {
        "ollama_host": "http://127.0.0.1:11434",
        "chat_model_text": "llama3.1:8b",
        "chat_model_vision": "llava:7b",
        "embedding_model": "mxbai-embed-large",
    }
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
        return default
    cfg = json.loads(path.read_text(encoding="utf-8"))
    default.update(cfg)
    return default


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def image_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def ingest(paths: List[Path], store: VectorStore, client: OllamaClient, embedding_model: str) -> None:
    supported = {".txt", ".md", ".csv", ".json", ".log", ".py"}
    files: List[Path] = []

    missing_paths: List[Path] = []
    for p in paths:
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            for ext in supported:
                files.extend(p.rglob(f"*{ext}"))
        else:
            missing_paths.append(p)

    if missing_paths:
        print("Caminho(s) não encontrado(s):")
        for mp in missing_paths:
            print(f" - {mp}")
        print(f"Pasta atual: {Path.cwd()}")

    if not files:
        print("Nenhum arquivo encontrado para ingestão.")
        return

    total_chunks = 0
    for file_path in files:
        text = read_text_file(file_path)
        chunks = chunk_text(text)
        if not chunks:
            continue
        for ch in chunks:
            emb = client.embed(embedding_model, ch)
            store.add(str(file_path), ch, emb)
            total_chunks += 1
        print(f"[OK] Indexado: {file_path} ({len(chunks)} chunks)")

    store.persist()
    print(f"\nConcluído. Chunks adicionados: {total_chunks}")


def build_system_prompt() -> str:
    return (
        "Você é uma IA assistente local e útil. "
        "Se houver contexto recuperado da base, use-o primeiro e cite a fonte pelo caminho do arquivo quando possível. "
        "Se não houver contexto suficiente, avise claramente e responda com o melhor esforço."
    )


def interactive_chat(
    store: VectorStore,
    client: OllamaClient,
    text_model: str,
    vision_model: str,
    embedding_model: str,
) -> None:
    print("\n=== IA Portátil (digite /sair para encerrar) ===")
    print("Comandos:")
    print("  /imagem CAMINHO   -> define uma imagem para próxima pergunta")
    print("  /limparimagem     -> remove imagem atual")
    print("  /pasta            -> mostra pasta atual (cwd)")

    image_path: Optional[Path] = None
    history: List[Dict[str, Any]] = [{"role": "system", "content": build_system_prompt()}]

    while True:
        user_input = input("\nVocê: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"/sair", "exit", "quit"}:
            print("Até mais!")
            return
        if user_input.lower().startswith("/imagem"):
            raw = user_input[len("/imagem") :].strip()
            p = resolve_input_path(raw)
            if not p.exists() or not p.is_file():
                print(f"Imagem não encontrada: {p}")
                print(f"Pasta atual: {Path.cwd()}")
                continue
            image_path = p
            print(f"Imagem ativa: {p}")
            continue
        if user_input.lower() == "/limparimagem":
            image_path = None
            print("Imagem removida.")
            continue
        if user_input.lower() == "/pasta":
            print(f"Pasta atual: {Path.cwd()}")
            continue

        q_emb = client.embed(embedding_model, user_input)
        refs = store.search(q_emb, top_k=5)

        context = ""
        if refs:
            context = "\n\n".join(
                f"[Fonte {i}: {ref['source']}]\n{ref['text']}" for i, ref in enumerate(refs, 1)
            )

        composed_user_prompt = user_input
        if context:
            composed_user_prompt = (
                f"Contexto recuperado da base local:\n{context}\n\nPergunta do usuário:\n{user_input}"
            )

        if image_path is not None:
            b64 = image_to_b64(image_path)
            msg = {"role": "user", "content": composed_user_prompt, "images": [b64]}
            answer = client.chat(vision_model, history + [msg])
        else:
            msg = {"role": "user", "content": composed_user_prompt}
            answer = client.chat(text_model, history + [msg])

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})

        print(f"\nIA: {answer}")
        if refs:
            print("\nFontes usadas:")
            for ref in refs:
                print(f" - {ref['source']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IA local portátil com texto + imagem")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Cria arquivos de configuração padrão")

    p_ingest = sub.add_parser("ingest", help="Indexa arquivos de texto para a base local")
    p_ingest.add_argument("paths", nargs="+", help="Arquivos/pastas para ingestão")

    sub.add_parser("chat", help="Abre chat interativo")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(DEFAULT_CONFIG)
    client = OllamaClient(cfg["ollama_host"])
    store = VectorStore(DEFAULT_STORE)

    if args.cmd == "init":
        print(f"Configuração pronta em: {DEFAULT_CONFIG}")
        print("Edite os modelos se quiser usar versões diferentes.")
        return
    try:
        if args.cmd == "ingest":
            ingest([resolve_input_path(p) for p in args.paths], store, client, cfg["embedding_model"])
            return
        if args.cmd == "chat":
            interactive_chat(
                store,
                client,
                cfg["chat_model_text"],
                cfg["chat_model_vision"],
                cfg["embedding_model"],
            )
    except RuntimeError as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
