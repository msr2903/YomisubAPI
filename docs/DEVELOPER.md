# Developer Documentation: Services Architecture

This document explains the internal workings of the `src/services/` folder in Yomisub API.

## Overview

The services folder contains the core logic for Japanese text analysis:

```
src/services/
├── __init__.py          # Package exports
├── analyzer.py          # Tokenization with SudachiPy
├── jmdict.py            # Dictionary lookup
├── verb.py              # Verb conjugation rules
├── adjective.py         # Adjective conjugation rules
└── conjugation.py       # Main analysis orchestration
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py (FastAPI)                     │
│                    Routes: /analyze, etc.                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    conjugation.py                            │
│              Main orchestration layer                        │
│  - analyze_full()     - COMPOUND_PHRASES dictionary         │
│  - analyze_simple()   - try_deconjugate_verb()              │
│  - build_conjugation_info()                                  │
└────────┬─────────────────────┬───────────────┬──────────────┘
         │                     │               │
         ▼                     ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   analyzer.py   │  │    verb.py      │  │  adjective.py   │
│   SudachiPy     │  │  Verb rules     │  │  Adj rules      │
│   tokenization  │  │  conjugate()    │  │  conjugate()    │
│                 │  │  deconjugate()  │  │  deconjugate()  │
└────────┬────────┘  └─────────────────┘  └─────────────────┘
         │
         ▼
┌─────────────────┐
│   jmdict.py     │
│   Dictionary    │
│   lookup()      │
└─────────────────┘
```

---

## 1. analyzer.py - Tokenization

### Purpose
Wraps SudachiPy for Japanese text tokenization.

### Key Components

```python
class JapaneseAnalyzer:
    """Singleton analyzer using SudachiPy."""
    
    tokenizer: Tokenizer  # SudachiPy tokenizer instance
    dictionary: Dictionary  # Sudachi dictionary
```

### SplitMode Selection

We use `SplitMode.C` (maximum splitting) to keep compound nouns together:

| Mode | Example | Result |
|------|---------|--------|
| A | 日本語 | 日本 + 語 |
| B | 日本語 | 日本語 |
| **C** | 日本語 | 日本語 |

### Token Properties

Each morpheme from SudachiPy provides:

```python
m.surface()        # Surface form: "食べた"
m.dictionary_form() # Base form: "食べる"
m.reading_form()   # Katakana reading: "タベタ"
m.part_of_speech() # POS tuple: ("動詞", "一般", ...)
```

---

## 2. jmdict.py - Dictionary Lookup

### Purpose
Fast English meaning lookups using jmdict-simplified JSON.

### Data Structure

```python
class JMDictionary:
    _index_kanji: dict[str, list[dict]]  # "日本語" -> [entry1, entry2, ...]
    _index_kana: dict[str, list[dict]]   # "にほんご" -> [entry1, ...]
```

### Lookup Priority

1. Try kanji index first (matches kanji forms)
2. Fall back to kana index (matches hiragana/katakana)

### Auto-Download Feature

If dictionary not found locally:
1. Query GitHub API for latest release
2. Download `jmdict-eng-*.json.gz`
3. Extract and load

---

## 3. verb.py - Verb Conjugation

### Purpose
Defines verb conjugation rules and provides conjugate/deconjugate functions.

### Enums

```python
class Conjugation(StrEnum):
    """Base conjugation forms."""
    NEGATIVE = "neg"      # ない form
    CONJUNCTIVE = "conj"  # masu-stem
    DICTIONARY = "dict"   # dictionary form
    CONDITIONAL = "cond"  # ば form
    TA = "ta"             # past tense
    TE = "te"             # te-form
    ...

class Auxiliary(StrEnum):
    """Auxiliary constructions."""
    POTENTIAL = "pot"     # can do
    MASU = "masu"         # polite
    NAI = "nai"           # negative
    TAI = "tai"           # want to
    TE_IRU = "teiru"      # progressive
    SERU_SASERU = "caus"  # causative
    RERU_RARERU = "pass"  # passive
    ...
```

### Conjugation Logic

The conjugation system uses a **stem + suffix** approach:

```python
# Godan verb: 書く (kaku)
stem = "kak"  # Remove u-ending

# Negative: a-column + ない
"書かない" = stem + "a" + "ない"

# Te-form: i-column + て (with sound change)
"書いて" = "kai" + "te"  # く→いて
```

### Sound Change Rules (Onbin)

For godan verbs, te/ta forms have special sound changes:

| Ending | Te-form | Ta-form | Example |
|--------|---------|---------|---------|
| く | いて | いた | 書く → 書いて |
| ぐ | いで | いだ | 泳ぐ → 泳いで |
| す | して | した | 話す → 話して |
| む/ぶ/ぬ | んで | んだ | 読む → 読んで |
| つ/う/る | って | った | 買う → 買って |

### Type 1 vs Type 2 Detection

```python
def is_verb_type2(pos_tuple: tuple) -> bool:
    """Check for ichidan (一段) markers in POS."""
    for p in pos_tuple:
        if "一段" in str(p) or "上一段" in str(p) or "下一段" in str(p):
            return True
    return False
```

### Deconjugation Algorithm

`deconjugate_verb()` works by **reverse pattern matching**:

```python
def deconjugate_verb(surface, base, type2, max_aux_depth):
    """
    1. Try to match surface against known conjugation patterns
    2. Peel off auxiliaries one at a time
    3. Return chain of (conjugation, auxiliaries)
    """
```

Example: `食べさせられた` → `食べる`

```
食べさせられた
  ├─ た (past) → 食べさせられ
  ├─ られ (passive) → 食べさせ
  └─ させ (causative) → 食べ (stem of 食べる)

Result: [SERU_SASERU, RERU_RARERU] + CONJUGATION.TA
```

---

## 4. adjective.py - Adjective Conjugation

### Purpose
Handles i-adjective and na-adjective conjugations.

### I-Adjective Rules

Base ends in い, which changes:

| Form | Suffix | Example |
|------|--------|---------|
| Negative | くない | 高くない |
| Past | かった | 高かった |
| Te-form | くて | 高くて |
| Adverb | く | 高く走る |
| Conditional | ければ | 高ければ |

### Na-Adjective Rules

Uses copula (だ/です) for conjugation:

| Form | Pattern | Example |
|------|---------|---------|
| Plain | だ | 静かだ |
| Polite | です | 静かです |
| Negative | じゃない/ではない | 静かじゃない |
| Past | だった | 静かだった |

---

## 5. conjugation.py - Main Orchestration

### Purpose
The main module that ties everything together.

### Key Data Structures

#### COMPOUND_PHRASES Dictionary

Maps first token → list of (phrase, meaning) tuples:

```python
COMPOUND_PHRASES = {
    "か": [
        ("かもしれない", "might; may; possibly"),
        ("かどうか", "whether or not"),
    ],
    "な": [
        ("なければならない", "must; have to"),
        ("なきゃいけない", "must; have to (casual)"),
    ],
    # ... 150+ patterns
}
```

#### GRAMMAR_MAP Dictionary

Maps particles/auxiliaries to their grammatical explanations:

```python
GRAMMAR_MAP = {
    "は": "topic marker",
    "が": "subject marker",
    "を": "object marker",
    "に": "direction/time/target",
    "で": "location/means",
    "よ": "emphasis",
    "ね": "confirmation/agreement",
    # ...
}
```

### Main Functions

#### `analyze_full(text: str) -> FullAnalyzeResponse`

Complete analysis including particles and grammar notes.

```python
def analyze_full(text):
    # 1. Tokenize with SudachiPy
    morphemes = tokenizer.tokenize(text, SplitMode.C)
    
    # 2. Try to match compound phrases
    phrase_match = try_match_compound_phrase(morphemes, i)
    
    # 3. Group verbs with auxiliaries
    while can_attach_morpheme(next_token):
        compound_surface += next_token.surface()
    
    # 4. Look up dictionary meaning
    meaning = jmdict.lookup(base_form)
    
    # 5. Try deconjugation
    conjugation_info = try_deconjugate_verb(surface, base, type2)
    
    # 6. Apply fallback pattern detection
    if conjugation_info is None:
        if "なきゃいけない" in surface:
            conjugation_info = "must; have to (casual)"
    
    # 7. Build response
    return FullAnalyzeResponse(phrases=[...])
```

#### `analyze_simple(text: str) -> SimpleAnalyzeResponse`

Vocabulary-focused analysis (filters grammar words).

Differences from `analyze_full`:
- Skips particles (は, が, を, etc.)
- Skips standalone auxiliaries (です, だ, た, etc.)
- Skips single-hiragana verbs (し, い, etc.)
- Returns `conjugation_hint` instead of full `ConjugationInfo`

#### `try_match_compound_phrase(morphemes, start_idx)`

Attempts to match grammar phrases starting at a given position:

```python
def try_match_compound_phrase(morphemes, start_idx):
    first_surface = morphemes[start_idx].surface()
    
    if first_surface not in COMPOUND_PHRASES:
        return None
    
    # Try to match longest phrase first
    for phrase, meaning in sorted(patterns, key=lambda x: -len(x[0])):
        if joined_surfaces.startswith(phrase):
            return (phrase, meaning, tokens_consumed)
    
    return None
```

### Morpheme Grouping Logic

The key insight is that Japanese conjugated forms span multiple morphemes:

```
食べられなかった
  ↓ SudachiPy tokenization
[食べ] [られ] [なかっ] [た]
  ↓ Grouping logic
[食べられなかった] (single verb compound)
```

Grouping rules:
1. Start with 動詞 (verb)
2. Attach: 助動詞 (auxiliary), 接尾辞 (suffix)
3. Attach: 非自立可能 (dependent forms)
4. Attach: 接続助詞 (connecting particles like て)
5. Stop at: 助詞 (particles), 名詞 (nouns)

---

## 6. Translation Hint Generation

### Purpose
Generate natural English hints for conjugated forms.

### Irregular Past Tense Handling

```python
IRREGULAR_PAST_TENSE = {
    "eat": "ate",      # not "eated"
    "go": "went",      # not "goed"
    "think": "thought", # not "thinked"
    # ... 50+ verbs
}

def make_past_tense(verb):
    if verb in IRREGULAR_PAST_TENSE:
        return IRREGULAR_PAST_TENSE[verb]
    return make_regular_past(verb)  # add -ed
```

### Hint Generation Pipeline

```python
def generate_translation_hint(base_meaning, auxiliaries, conjugation):
    hint = extract_first_verb(base_meaning)  # "to eat" → "eat"
    
    # Apply auxiliary transformations
    for aux in auxiliaries:
        if aux == NAI:
            hint = f"not {hint}"
        elif aux == TAI:
            hint = f"want to {hint}"
        elif aux == TE_IRU:
            hint = f"is {hint}ing"
    
    # Apply conjugation
    if conjugation == TA:
        hint = make_past_tense(hint)  # "eat" → "ate"
    elif conjugation == TE:
        hint = f"{hint} and..."
    
    return hint
```

---

## 7. Adding New Grammar Patterns

To add a new grammar pattern:

### Step 1: Add to COMPOUND_PHRASES

```python
COMPOUND_PHRASES = {
    # Add new key if first token doesn't exist
    "ところ": [
        ("ところだ", "about to; just did"),
        ("ところで", "by the way"),
    ],
}
```

### Step 2: Check Sudachi Tokenization

Use `/tokenize` endpoint to verify how Sudachi splits the phrase:

```bash
curl -X POST http://localhost:8000/tokenize \
  -d '{"text": "食べたところだ"}'
```

### Step 3: Add Fallback (Optional)

If deconjugation misses the pattern, add to fallback:

```python
# In analyze_full() and analyze_simple()
if "ところだ" in compound_surface:
    fallback_summary = "about to; just did"
```

---

## 8. Performance Considerations

### Dictionary Loading
- JMDict is loaded once at startup (~3-5 seconds)
- Uses singleton pattern with `@lru_cache`
- 214k+ entries indexed in memory

### Tokenization
- SudachiPy is fast (~1ms per sentence)
- Dictionary loaded in memory

### Optimization Tips
- Avoid re-tokenizing same text
- Use `analyze_simple` for vocabulary-only needs
- Batch requests when possible

---

## 9. Testing

### Manual Testing

```bash
# Test specific patterns
curl -X POST http://localhost:8000/analyze_full \
  -H "Content-Type: application/json" \
  -d '{"text": "食べなければならない"}'

# Check tokenization
curl -X POST http://localhost:8000/tokenize \
  -d '{"text": "食べなければならない"}'
```

### Unit Testing

```python
# scripts/test_conjugation.py
from services.verb import deconjugate_verb

def test_causative_passive():
    results = deconjugate_verb("食べさせられた", "食べる", type2=True)
    assert results[0].auxiliaries == (Auxiliary.SERU_SASERU, Auxiliary.RERU_RARERU)
    assert results[0].conjugation == Conjugation.TA
```

---

## 10. Common Issues and Solutions

### Issue: Grammar pattern not detected

**Solution:** Check if first token matches COMPOUND_PHRASES key:
```python
# Wrong: Sudachi splits かも separately
"かもしれない"  # Key should be "か", not "かも"

# Correct: Use what Sudachi produces as first token
curl -X POST /tokenize -d '{"text": "かもしれない"}'
# → か | も | しれ | ない
# Use "か" as the key
```

### Issue: Wrong meaning shown

**Solution:** Add to meaning overrides or check JMDict entry order

### Issue: Conjugation not recognized

**Solution:** 
1. Check if pattern is in verb.py rules
2. Add fallback pattern in conjugation.py
3. Verify Sudachi tokenization matches expectations
