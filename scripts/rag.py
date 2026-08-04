"""Shared RAG helpers: document extraction, chunking, ChromaDB index + retrieval."""
import hashlib
import os
import re
import sys

import chromadb
from chromadb.config import Settings

RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")
CHROMA_PATH = os.path.join(RAG_ROOT, "chroma_db")
COLLECTION = "knowledge"
CHUNK_CHARS = 1200
OVERLAP_CHARS = 200


class NoDocumentText(Exception):
    pass


def extract_text(path):
    """Extract plain text from pdf/md/txt."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        import fitz

        doc = fitz.open(path)
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    if ext in (".md", ".txt"):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    raise NoDocumentText(f"Unsupported file type: {path}")


def split_sections(text):
    """Split markdown-ish text into (header, body) sections on heading lines."""
    lines = text.splitlines()
    sections = []
    cur_header = "DOCUMENT"
    cur_body = []
    for line in lines:
        if re.match(r"^#{1,4}\s", line.strip()):
            if cur_body:
                sections.append((cur_header, "\n".join(cur_body)))
            cur_header = line.strip()
            cur_body = []
        else:
            cur_body.append(line)
    if cur_body:
        sections.append((cur_header, "\n".join(cur_body)))
    return sections


def chunk_text(text, chunk_chars=CHUNK_CHARS, overlap=OVERLAP_CHARS):
    """Split text into overlapping chunks at paragraph/word boundaries."""
    chunks = []
    sections = split_sections(text)
    for header, body in sections:
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        buf = ""
        for p in paras:
            if len(buf) + len(p) + 2 > chunk_chars and buf:
                chunks.append(header + "\n\n" + buf.strip())
                buf = buf[-overlap:] if len(buf) > overlap else ""
            buf = (buf + "\n\n" + p).strip()
        if buf:
            chunks.append(header + "\n\n" + buf.strip())
    if not chunks and text.strip():
        chunks = [text.strip()]
    return chunks


def chunk_id(source, idx):
    h = hashlib.sha1(f"{source}:{idx}".encode("utf-8")).hexdigest()[:16]
    return f"{os.path.basename(source)}::{idx}::{h}"


def get_client():
    os.makedirs(CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection(client, name=COLLECTION):
    return client.get_or_create_collection(
        name, metadata={"hnsw:space": "cosine"}
    )


def retrieve(query_text, embed_fn, top_k=3, collection=None):
    """Embed query and return top-k chunks from the knowledge collection."""
    from ollama_client import embed as default_embed

    embed_fn = embed_fn or default_embed
    if collection is None:
        client = get_client()
        collection = get_collection(client)
    q = embed_fn(query_text)
    res = collection.query(query_embeddings=[q], n_results=top_k)
    docs = res.get("documents", [[]])[0] or []
    metas = res.get("metadatas", [[]])[0] or []
    distances = res.get("distances", [[]])[0] or []
    return [
        {"text": d, "metadata": m, "distance": dist}
        for d, m, dist in zip(docs, metas, distances)
    ]


def index_knowledge(target, embed_many_fn=None, collection=None):
    """Walk a folder (or index a single file), chunk all supported docs, embed,
    and upsert into ChromaDB. Re-indexing is idempotent (upsert by chunk id)."""
    from ollama_client import embed_many as default_embed_many

    embed_many_fn = embed_many_fn or default_embed_many
    if collection is None:
        client = get_client()
        collection = get_collection(client)

    files = []
    if os.path.isfile(target):
        if target.lower().endswith((".pdf", ".md", ".txt")):
            files.append(target)
    else:
        for root, _dirs, names in os.walk(target):
            for n in sorted(names):
                if n.lower().endswith((".pdf", ".md", ".txt")):
                    files.append(os.path.join(root, n))

    total_chunks = 0
    for path in files:
        try:
            text = extract_text(path)
        except NoDocumentText as e:
            print(f"  skip {path}: {e}")
            continue
        chunks = chunk_text(text)
        if not chunks:
            continue
        ids = [chunk_id(path, i) for i in range(len(chunks))]
        docs = chunks
        metas = [
            {"source": os.path.basename(path), "chunk": i, "path": path}
            for i in range(len(chunks))
        ]
        for start in range(0, len(docs), 20):
            batch_slice = slice(start, start + 20)
            emb = embed_many_fn(docs[batch_slice])
            collection.upsert(
                ids=ids[batch_slice],
                embeddings=emb,
                documents=docs[batch_slice],
                metadatas=metas[batch_slice],
            )
        total_chunks += len(chunks)
        print(f"  indexed {os.path.basename(path)}: {len(chunks)} chunks")

    print(f"Total chunks indexed: {total_chunks}")
    return total_chunks


def collection_count():
    client = get_client()
    return get_collection(client).count()
