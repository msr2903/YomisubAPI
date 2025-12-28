---
title: YomisubAPI
emoji: 📚
colorFrom: red
colorTo: indigo
sdk: docker
pinned: false
short_description: Japanese text analysis API for language learning
---

# Yomisub API 📚

A Japanese text analysis API for language learning. Built with FastAPI, SudachiPy, and JMDict.

## Features

- 🔤 **Tokenization** — Break down Japanese text into words using SudachiPy (full dictionary)
- 📖 **Dictionary Lookup** — English meanings via JMDict (214k+ entries)
- 🗣️ **Readings** — Hiragana readings for all words
- 📑 **Grammar Support** — Explanations for particles, auxiliaries, and pronouns
- ⚡ **Fast** — In-memory dictionary with O(1) lookups
- 🚫 **Name Filtering** — Automatically skips untranslated katakana (names)
- 📱 **iOS Support** — Analyze text directly from your iPhone or iPad with Netflix, Apple TV, or any other streaming app with subtitles

## iOS Shortcut (Netflix, Apple TV, etc. )

You can use Yomisub API directly on your iOS device with streaming app using this Apple Shortcut:

👉 **[Install Yomisub iOS Shortcut](https://www.icloud.com/shortcuts/520d8ae630684ad99b7a495e306cc64a)**

This shortcut allows you to send subtitles from any streaming app with subtitles to your hosted API (the default is my huggingface API) and receive the notifications in seconds.
Just set a trigger to the shortcut (Back tap, Action button, etc. ) after found a subtitle you want to analyze, then the notification will be sent. 

Example in Netflix:
<img width="1218" height="563" alt="IMG_4481" src="https://github.com/user-attachments/assets/ebbc952f-9b72-45a3-9b9c-ed050dcbc295" />


## Quick Start to Host your own API

### 1. Install Dependencies
```bash
uv sync
```

### 2. Download JMDict Dictionary
```bash
make update-dict
# or manually:
./scripts/update_jmdict.sh
```

### 3. Run Development Server
```bash
make dev
```

API available at `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Full JSON with tokens, readings, POS, meanings |
| `POST` | `/analyze_simple` | Clean text output (vocabulary only, filtered) |
| `POST` | `/analyze_full` | All tokens including grammar words |
| `POST` | `/tokenize` | Raw SudachiPy tokenization (for debugging) |
| `GET` | `/health` | Health check |

### Example Request
```bash
curl -X POST "http://localhost:8000/analyze_simple" \
     -H "Content-Type: application/json" \
     -d '{"text": "日本語を勉強しています"}'
```

### Example Response
```json
{
  "result": "日本語 (にほんご) = Japanese (language)\n勉強 (べんきょう) = study"
}
```

## Docker

### Build & Run
```bash
docker build -t yomisub .
docker run -p 8000:8000 yomisub
```

### With Docker Compose (optional)
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
```

## Project Structure

```
YomisubAPI/
├── pyproject.toml          # Dependencies (uv)
├── Makefile                 # Dev commands
├── Dockerfile               # Production build
├── data/
│   └── jmdict-eng.json      # JMDict dictionary (110MB)
├── scripts/
│   └── update_jmdict.sh     # Dictionary updater
└── src/
    ├── main.py              # FastAPI app
    └── services/
        ├── analyzer.py      # SudachiPy tokenization + grammar
        └── jmdict.py        # JMDict lookup service
```

## Updating the Dictionary

JMDict is updated monthly. To get the latest:

```bash
make update-dict
```

Or set up a cron job:
```bash
# Monthly update (1st of each month at midnight)
0 0 1 * * cd /path/to/project && ./scripts/update_jmdict.sh
```

## Tech Stack

- **Framework:** FastAPI
- **Tokenizer:** SudachiPy (with sudachidict-full)
- **Dictionary:** JMDict via jmdict-simplified
- **Package Manager:** uv (by Astral)
- **Python:** 3.12+

## Deployment

Optimized for free cloud services:

| Service | Command |
|---------|---------|
| Railway | `railway up` |
| Fly.io | `fly launch` |
| Render | Connect GitHub repo |

## License

MIT
