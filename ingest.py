"""
ingest.py — Feed URLs or PDF files into your ChromaDB knowledge base.

Usage:
  python ingest.py --url https://wiki.example.com/destiny2
  python ingest.py --pdf my_guide.pdf
  python ingest.py --url URL1 --url URL2 --pdf file.pdf
"""

import argparse
import hashlib
import os
import sys

import chromadb
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

# ── Config ──────────────────────────────────────────────────────────────────
CHROMA_DIR   = "./chroma_db"
COLLECTION   = "gaming_knowledge"
EMBED_MODEL  = "all-MiniLM-L6-v2"   # free, runs locally
CHUNK_SIZE   = 500                   # characters per chunk
CHUNK_OVERLAP = 50

# ── Setup ────────────────────────────────────────────────────────────────────
embedder   = SentenceTransformer(EMBED_MODEL)
chroma     = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma.get_or_create_collection(COLLECTION)


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 80]   # drop tiny tail chunks


def add_chunks(chunks: list[str], source: str):
    """Embed chunks and upsert into ChromaDB."""
    if not chunks:
        print(f"No content extracted from {source}")
        return

    embeddings = embedder.encode(chunks).tolist()
    ids = [hashlib.md5(f"{source}::{i}".encode()).hexdigest() for i in range(len(chunks))]
    metadatas = [{"source": source} for _ in chunks]

    collection.upsert(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    print(f"  ✓  Added {len(chunks)} chunks from {source}")


def ingest_url(url: str):
    print(f"\n Fetching {url}")
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        print(f" Failed to fetch URL: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    add_chunks(chunk_text(text), source=url)


def ingest_pdf(path: str):
    print(f"\n Reading {path}")
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        add_chunks(chunk_text(text), source=path)
    except Exception as e:
        print(f"  ✗  Failed to read PDF: {e}")


def list_sources():
    results = collection.get(include=["metadatas"])
    sources = sorted({m["source"] for m in results["metadatas"]})
    if sources:
        print(f"\n Knowledge base contains {len(sources)} source(s):")
        for s in sources:
            print(f"   • {s}")
    else:
        print("\n Knowledge base is empty. Run ingest.py with --url or --pdf.")


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest URLs or PDFs into your gaming chatbot knowledge base.")
    parser.add_argument("--url",  action="append", default=[], metavar="URL",  help="URL to scrape")
    parser.add_argument("--pdf",  action="append", default=[], metavar="FILE", help="PDF file to ingest")
    parser.add_argument("--list", action="store_true", help="List all ingested sources")
    args = parser.parse_args()

    if args.list:
        list_sources()
        sys.exit(0)

    if not args.url and not args.pdf:
        parser.print_help()
        sys.exit(1)

    for url in args.url:
        ingest_url(url)
    for pdf in args.pdf:
        ingest_pdf(pdf)

    print("\n Ingestion complete!")
    list_sources()
