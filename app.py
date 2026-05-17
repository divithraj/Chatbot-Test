"""
app.py — Streamlit chat UI for the gaming knowledge chatbot.
Run with: streamlit run app.py
"""

import streamlit as st
import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Knowledge Bot",
    page_icon="🎮",
    layout="centered",
)

# ── Custom styling ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3 { font-family: 'Rajdhani', sans-serif; letter-spacing: 1px; }

  .stChatMessage { border-radius: 12px; }

  .source-pill {
    display: inline-block;
    background: #1a1a2e;
    color: #7c83fd;
    border: 1px solid #7c83fd44;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    margin: 2px 4px 2px 0;
    font-family: 'Inter', monospace;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: middle;
  }

  .sources-bar {
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid #ffffff11;
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #888;
  }
</style>
""", unsafe_allow_html=True)

# ── Check API key ─────────────────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    st.error(" GROQ_API_KEY not found. Add it to your .env file and restart.")
    st.stop()

# ── Import chatbot (after env check) ─────────────────────────────────────────
from chatbot import chat, collection

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎮 Gaming Knowledge Bot")
    st.markdown("---")

    # KB stats
    count = collection.count()
    if count > 0:
        st.success(f"{count} chunks in knowledge base")
        results = collection.get(include=["metadatas"])
        sources = sorted({m["source"] for m in results["metadatas"]})
        with st.expander(f"{len(sources)} source(s) loaded"):
            for s in sources:
                label = s if len(s) < 50 else "..." + s[-47:]
                st.markdown(f"• `{label}`")
    else:
        st.warning("📭 Knowledge base is empty")
        st.markdown("""
**To add content, run in your terminal:**
```bash
python ingest.py --url https://www.destinypedia.com/Destiny_2
python ingest.py --pdf my_guide.pdf
```
        """)

    st.markdown("---")

    # URL ingestion from sidebar
    st.markdown("#### Add a URL")
    new_url = st.text_input("Paste a URL to ingest", placeholder="https://wiki.example.com/page")
    if st.button("Ingest URL", use_container_width=True) and new_url:
        with st.spinner("Scraping and embedding..."):
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from ingest import ingest_url
                ingest_url(new_url)
                st.success("Ingested!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown("# Knowledge Bot")
st.markdown("Ask me anything of what you've fed me!  I started off as a gaming knowledge base, but I can chat about general topics too.  Please add in knowledge sources if needed.")
st.markdown("---")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
if not st.session_state.messages:
    st.markdown("""
<div class="empty-state">
  <h3>No messages yet</h3>
  <p>Ask a question below, or add some sources in the sidebar first.</p>
  <p>Try: <em>"What subclasses are available in Destiny 2?"</em></p>
</div>
""", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            pills = "".join(
                f'<span class="source-pill" title="{s}">🔗 {s[:40] + "..." if len(s) > 40 else s}</span>'
                for s in msg["sources"]
            )
            st.markdown(
                f'<div class="sources-bar"><small>Sources:</small> {pills}</div>',
                unsafe_allow_html=True
            )

# Chat input
if prompt := st.chat_input("Ask away"):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            answer, sources = chat(prompt, history)

        st.markdown(answer)
        if sources:
            pills = "".join(
                f'<span class="source-pill" title="{s}"> {s[:40] + "..." if len(s) > 40 else s}</span>'
                for s in sources
            )
            st.markdown(
                f'<div class="sources-bar"><small>Sources:</small> {pills}</div>',
                unsafe_allow_html=True
            )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })
