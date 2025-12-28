---
title: Yomisub API
emoji: 📚
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# Yomisub API

A comprehensive Japanese text analysis API with advanced conjugation support, powered by SudachiPy and JMDict.

## Features

- 🔍 **Smart Tokenization** - Uses SudachiPy with SplitMode.C to keep compound nouns together
- 📚 **Auto-Download Dictionary** - JMDict automatically downloaded from latest release (214k+ entries)
- 🧩 **Conjugation Analysis** - Deconjugate verbs and adjectives with detailed breakdowns
- 🎯 **30+ Auxiliary Constructions** - Potential, passive, causative, benefactive, and more
- 📝 **150+ Grammar Patterns** - Common JLPT N5-N2 grammar phrases detected automatically
- 📑 **Grammar Support** - Explanations for particles, auxiliaries, and pronouns
- 🌐 **Natural English** - Uses lemminflect for accurate past tense (ate, went, thought)
- 🚫 **Name Filtering** - Automatically skips untranslated katakana (names)
- 📱 **iOS Support** - Analyze text directly from your iPhone or iPad with Netflix, Apple TV, or any other streaming app

## iOS Shortcut (Netflix, Apple TV, etc.)

You can use Yomisub API directly on your iOS device with streaming apps using this Apple Shortcut:

👉 **[Install Yomisub iOS Shortcut](https://www.icloud.com/shortcuts/520d8ae630684ad99b7a495e306cc64a)**

This shortcut allows you to send subtitles from any streaming app to your hosted API (the default is my Hugging Face API) and receive notifications in seconds.

Example in Netflix:
<img width="1218" height="563" alt="IMG_4481" src="https://github.com/user-attachments/assets/ebbc952f-9b72-45a3-9b9c-ed050dcbc295" />

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/msr2903/YomisubAPI
cd YomisubAPI

# Install dependencies with uv
uv sync

# Run the server
uv run uvicorn src.main:app --reload
```

### API Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `POST /analyze` | Structured token analysis | Apps with custom UI |
| `POST /analyze_simple` | Vocabulary-focused | Study/flashcard apps |
| `POST /analyze_full` | Complete grammar breakdown | Grammar study |
| `POST /deconjugate` | Verb/adjective analysis | Conjugation learning |
| `POST /conjugate` | Generate conjugations | Reference tool |
| `POST /tokenize` | Raw tokenization | Debugging |

## Example Usage

### Analyze Text (Simple)

```bash
curl -X POST http://localhost:8000/analyze_simple \
  -H "Content-Type: application/json" \
  -d '{"text": "日本語を勉強しなければならない"}'
```

**Response:**
```json
{
  "vocabulary": [
    {"word": "日本語", "base": "日本語", "reading": "にほんご", "meaning": "Japanese (language)"},
    {"word": "勉強", "base": "勉強", "reading": "べんきょう", "meaning": "study"},
    {"word": "しなければならない", "base": "する", "reading": "する", "meaning": "to do", "conjugation_hint": "must; have to"}
  ],
  "count": 3
}
```

### Deconjugate Verb

```bash
curl -X POST http://localhost:8000/deconjugate \
  -H "Content-Type: application/json" \
  -d '{"word": "食べられなかった", "type": "ichidan"}'
```

**Response:**
```json
{
  "word": "食べられなかった",
  "base": "食べる",
  "conjugation": {
    "chain": [
      {"type": "RERU_RARERU", "english": "passive/potential"},
      {"type": "NAI", "english": "negative"},
      {"type": "TA", "english": "past"}
    ],
    "summary": "passive/potential + negative + past",
    "translation_hint": "couldn't eat"
  }
}
```

## Supported Conjugations

### Verb Auxiliaries

| Category | Auxiliaries |
|----------|-------------|
| **Potential/Passive** | れる/られる, せる/させる, causative-passive |
| **Desire** | たい, たがる, ほしい |
| **Aspect** | ている, てある, てみる, ておく, てしまう |
| **Direction** | ていく, てくる |
| **Benefactive** | てあげる, てもらう, てくれる |
| **Degree** | すぎる, やすい, にくい |
| **Compound** | かける, きる, こむ, だす, なおす |

### Grammar Patterns Detected

| Category | Examples |
|----------|----------|
| **Obligation** | なければならない, ないといけない, なきゃいけない |
| **Permission** | てもいい, てはいけない |
| **Conjecture** | かもしれない, はずだ, だろう |
| **Appearance** | らしい, みたいだ, ようだ, っぽい |
| **Purpose** | ために, ように |
| **Extent** | ほど, だけ, ばかり |
| **Time** | うちに, たびに, ところだ |

## Project Structure

```
YomisubAPI/
├── src/
│   ├── main.py              # FastAPI routes
│   ├── models.py            # Pydantic models
│   └── services/
│       ├── analyzer.py      # Japanese analyzer
│       ├── conjugation.py   # Conjugation logic
│       ├── verb.py          # Verb conjugation rules
│       ├── adjective.py     # Adjective conjugation
│       └── jmdict.py        # Dictionary lookup
├── data/
│   └── jmdict-eng.json.gz   # Auto-downloaded on first run
├── docs/
│   ├── index.html           # API Documentation
│   └── developer.html       # Developer Guide
└── pyproject.toml
```

## Capabilities & Limitations

### ✅ Verified Capabilities
- **Smart Counters**: Correctly identifies counters like `一本` (one long thing) vs `本` (book) using fuzzy phonetic matching (`pon` ≈ `hon`).
- **Complex Conjugations**: Deconjugates chains like `食べさせられた` (Causative-Passive) or `なきゃ` (Casual Must).
- **Rich Vocabulary**: Includes Adverbs, Conjunctions, and Onomatopoeia (`ドキドキ`, `ペラペラ`).
- **Clean Output**: `/analyze_simple` provides a noise-free vocabulary list, ideal for flashcards.
- **Deep Grammar**: `/analyze_full` provides POS tags (`Transitive`, `Slang`, `Humble`) and breakdown of every particle.

### ⚠️ Known Limitations
- **Homographs**: Contextual reading selection (e.g. `辛い` as *spicy* vs *painful*) depends on Sudachi's tokenization model and may occasionally be incorrect.
- **Idioms**: Multi-word idioms (e.g. `腹が立つ` - to get angry) are usually split into individual words (`Stomach` + `Stand`) unless they are single dictionary tokens.
- **Slang Negations**: In simple analysis, slang negations like `〜んじゃねー` might be filtered out, leaving only the main verb. Use full analysis for these.
- **Proper Names**: Names not in the main JMDict (e.g. specific surnames) may appear without definitions.

## Documentation

- **[API Documentation](docs/index.html)** - Endpoints, examples, and grammar patterns
- **[Developer Guide](docs/developer.html)** - Architecture, adding grammar, and internals

## Live API

🚀 **[Try the API on Hugging Face](https://huggingface.co/spaces/msr2903/YomisubAPI)**

## License

MIT License
