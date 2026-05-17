# 🎮 Gaming Knowledge Bot

A RAG chatbot that answers questions about your favorite games using sources you feed it.

## Setup

1. **Create & activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Mac/Linux
   venv\Scripts\activate           # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your Groq API key**
   - Sign up free at https://console.groq.com
   - Create a `.env` file in this folder:
   ```
   GROQ_API_KEY=your_key_here
   ```

## Usage

### Step 1 — Feed it some content
```bash
# Ingest a wiki URL
python ingest.py --url https://www.destinypedia.com/Destiny_2

# Ingest multiple URLs
python ingest.py --url https://swtor.fandom.com/wiki/Star_Wars:_The_Old_Republic

# Ingest a PDF guide
python ingest.py --pdf my_guide.pdf

# See what's in your knowledge base
python ingest.py --list
```

### Step 2 — Launch the chatbot
```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`

You can also add URLs directly from the sidebar in the UI.

## Swapping the LLM model

In `chatbot.py`, change `GROQ_MODEL` to any free Groq model:
- `llama3-8b-8192` — fastest (default)
- `mixtral-8x7b-32768` — smarter, longer context
- `llama3-70b-8192` — most capable

## Project structure
```
gaming-chatbot/
├── .env              ← your API key (never commit this)
├── requirements.txt
├── ingest.py         ← add URLs/PDFs to knowledge base
├── chatbot.py        ← RAG core logic
├── app.py            ← Streamlit UI
└── chroma_db/        ← auto-created when you first ingest
```
