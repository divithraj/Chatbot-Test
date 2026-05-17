"""
chatbot.py — RAG core: retrieve relevant chunks, build prompt, call Groq.
"""

import os
from groq import Groq
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
CHROMA_DIR    = "./chroma_db"
COLLECTION    = "gaming_knowledge"
EMBED_MODEL   = "all-MiniLM-L6-v2"
GROQ_MODEL    = "llama-3.3-70b-versatile"     # free & fast; swap to mixtral-8x7b-32768 for longer context
TOP_K         = 5                    # chunks to retrieve per query
MAX_HISTORY   = 6                    # messages to keep in sliding window

# ── Setup ────────────────────────────────────────────────────────────────────
embedder   = SentenceTransformer(EMBED_MODEL)
chroma     = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma.get_or_create_collection(COLLECTION)
client     = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are a knowledgeable gaming assistant specializing in games like Destiny 2 and SWTOR (Star Wars: The Old Republic). 

Answer questions using the provided context from the knowledge base. If the context doesn't contain enough information, say so honestly and share what general knowledge you have. Always be helpful, specific, and enthusiastic about gaming.

When referencing information, mention where it came from if a source is available."""


def retrieve(query: str) -> tuple[str, list[str]]:
    """Embed query and fetch top-k relevant chunks from ChromaDB."""
    query_embedding = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(TOP_K, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    if not results["documents"] or not results["documents"][0]:
        return "", []

    chunks    = results["documents"][0]
    sources   = [m["source"] for m in results["metadatas"][0]]
    distances = results["distances"][0]

    # Filter out low-relevance chunks (distance > 1.2 is usually noise)
    filtered = [(c, s) for c, s, d in zip(chunks, sources, distances) if d < 1.2]
    if not filtered:
        return "", []

    chunks, sources = zip(*filtered)
    context = "\n\n---\n\n".join(
        f"[Source: {s}]\n{c}" for c, s in zip(chunks, sources)
    )
    return context, list(set(sources))


def build_messages(history: list[dict], user_query: str, context: str) -> list[dict]:
    """Build the message list for the Groq API call."""
    # Sliding window — keep last MAX_HISTORY messages
    recent_history = history[-MAX_HISTORY:]

    context_block = (
        f"Relevant information from your knowledge base:\n\n{context}\n\n---\n\n"
        if context else
        "Note: No relevant information found in the knowledge base for this query. Answer from general knowledge.\n\n---\n\n"
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += recent_history
    messages.append({"role": "user", "content": context_block + user_query})
    return messages


def chat(user_query: str, history: list[dict]) -> tuple[str, list[str]]:
    """
    Main entry point. Returns (answer, sources_used).
    history: list of {"role": "user"/"assistant", "content": "..."} dicts
    """
    context, sources = retrieve(user_query)
    messages = build_messages(history, user_query, context)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content
    return answer, sources
