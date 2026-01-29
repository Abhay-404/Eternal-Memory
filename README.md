# Eternal Memory - Personal Memory System

A personal second brain that automatically processes daily audio recordings into organized, searchable memories with intelligent, evolving context.

## Features

- **Google Drive Sync**: Automatic audio sync from Drive folder
- **Multi-language Transcription**: Supports Hindi, English, and Hinglish with Gemini(You can try other tts also)
- **Intelligent Memory**: LLM-curated primary context (500 words) and short-term memory (6000-7000 words)
- **Hierarchical Summaries**: Auto-creates daily → weekly → monthly summaries
- **Hybrid Search**: 70% Vector + 30% BM25 semantic search using ChromaDB
- **Conversational Queries**: Natural language interface with multi-turn function calling

## Installation

```bash
pip install -r requirements.txt
```

Create `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

## Quick Start

### 1. Setup Google Drive (One-time)

Follow `DRIVE_SETUP.md` to:
- Create Google Cloud project
- Enable Drive API
- Download `credentials.json`

Your Drive folder: ..

### 2. Upload Audio

Upload daily audio recordings to your Drive folder. Date is automatically extracted from file upload time.

### 3. Update Memory

```bash
python update_today_memory.py
```

This will:
- Download audio from Drive (organized by date)
- Transcribe each audio file separately
- Create daily summary (300-400 words)
- Update primary context (500 words)
- Update short-term memory (6000-7000 words)
- Embed in vector database
- Auto-create weekly summary (if week complete)
- Auto-create monthly summary (if month complete)
- Delete from Drive after successful processing

### 4. Query Your Memories

```bash
python query.py
```

Ask naturally:
- "What did I do yesterday?"
- "Tell me about last month"
- "What projects am I working on?"

The system automatically decides which memory tier to use via function calling.

## Architecture

```
MY_BRAIN/
├── update_today_memory.py   # Main script (sync + process audio)
├── query.py                 # Query interface
├── credentials.json         # Google OAuth credentials (you create)
├── token.json              #  auth token
├── src/
│   ├── core/               # LLM client, embeddings
│   ├── database/           # Vector database (ChromaDB)
│   ├── memory/             # Memory 
│   ├── utils/               # Config & Helpers
│   └── services/           # Drive sync, audio processing
├── data/
│   ├── audio/              # Downloaded audio (by date)
│   ├── summaries/
│   │   ├── daily/          # Daily summaries
│   │   ├── weekly/         # Weekly summaries (auto-created)
│   │   └── monthly/        # Monthly summaries (auto-created)
│   ├── primary_context.json        # 500 words - core facts
│   ├── short_term_memory.json      # 6000-7000 words - major info + last 14 days
│   └── vector_store/               # Searchable embeddings
```

<img width="8192" height="4736" alt="Mermaid Chart - Create complex, visual diagrams with text -2026-01-29-153819" src="https://github.com/user-attachments/assets/2b6ce9da-8feb-4451-90bb-fe90def91d70" />




## Memory Tiers

### 1. Primary Context (500 words)
- Always loaded with every LLM call
- Identity, goals, relationships, health, preferences
- Updates daily based on new information

### 2. Short-term Memory (6000-7000 words)
- Intelligent working memory curated by LLM
- Everything major about you + last 14 days events
- Uses current memory + today's summary + recent weekly context
- LLM decides: KEEP, ADD, UPDATE, REMOVE

### 3. Hierarchical Summaries
- **Daily** (300-400 words): Activities, work, people, thoughts, mood
- **Weekly** (400-600 words): Auto-created when week completes (Sunday)
- **Monthly** (600-1000 words): Auto-created when month completes

### 4. Long-term Memory
- All summaries stored in ChromaDB vector database
- Hybrid search (70% Vector + 30% BM25)
- Searchable by semantic meaning and keywords

## Workflow

### Daily Routine:

1. **Record audio** (phone, meetings, thoughts)
2. **Upload to Drive folder**
3. **Run**: `python update_today_memory.py`
4. **Query**: `python query.py`

### If you miss 2-3 days:

Just run `update_today_memory.py` - it processes all pending audio automatically!

## How It Works

### Date Detection:
- Uses Drive file `createdTime` metadata
- Automatically groups multiple files per day
- No filename requirements

### Audio Processing:
- Each audio file transcribed separately
- All transcriptions combined for daily summary
- Supports: mp3, wav, m4a, aac
- Languages: Hindi, English, Hinglish (mixed) etc.

### Memory Updates:
- Daily summary feeds into primary context
- Primary context always stays under 500 words
- Short-term memory intelligently maintains last 14 days
- Weekly/monthly summaries auto-created when periods complete

### Query System:
- Primary context always loaded (fast)
- LLM decides via function calling:
  - Recent question → Fetch short-term memory
  - Historical question → Search long-term memory
- Maintains conversation history for follow-ups

## Configuration

### Change Drive Folder:

Edit `update_today_memory.py`:
```python
FOLDER_ID = "your_folder_id_here"
```


## Tech Stack

- **LLM**: Google Gemini 2.0 Flash
- **Embeddings**: Gemini text-embedding-004
- **Vector DB**: ChromaDB
- **Search**: Hybrid (Vector + BM25)
- **Language**: Python 3.8+
- **Drive API**: Google Drive API v3

## Notes

- Designed for single-user personal use
- Audio files deleted from Drive after processing (keeps Drive clean)
- Works best with daily 5-30 minute recordings
- Supports multilingual input (Hindi/English/Hinglish)
- Weekly summaries created every Sunday
- Monthly summaries created on last day of month

## Things to try 
- Graphrag(https://arxiv.org/abs/2501.13956)
- Better dataset
- Speaker identification 
