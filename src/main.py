"""Yomisub FastAPI application - Japanese text analysis API."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.analyzer import JapaneseAnalyzer


# ============================================================================
# Pydantic Models
# ============================================================================


class AnalyzeRequest(BaseModel):
    """Request body for text analysis."""

    text: str = Field(..., min_length=1, max_length=10000, description="Japanese text to analyze")


class TokenResponse(BaseModel):
    """Single token in the analysis response."""

    word: str = Field(..., description="Surface form (as written)")
    base: str = Field(..., description="Dictionary/base form")
    reading: str = Field(..., description="Reading in hiragana")
    pos: str = Field(..., description="Part of speech")
    meaning: str | None = Field(None, description="English meaning")


class AnalyzeResponse(BaseModel):
    """Response body for text analysis."""

    tokens: list[TokenResponse]
    count: int = Field(..., description="Number of tokens found")

# ============================================================================
# Application Lifespan
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize heavy resources on startup."""
    # Pre-warm the analyzer (loads SudachiPy dict and jamdict)
    _ = JapaneseAnalyzer.get_instance()
    yield


# ============================================================================
# FastAPI Application
# ============================================================================


app = FastAPI(
    title="Yomisub API",
    description="Japanese text analysis API for language learning. "
    "Tokenizes text, extracts readings, and provides English definitions.",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "yomisub"}


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Detailed health check."""
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze Japanese text and return tokenized information.

    - **text**: Japanese text to analyze (1-10000 characters)

    Returns a list of tokens with:
    - Surface form (word as written)
    - Base/dictionary form
    - Reading (katakana)
    - Part of speech
    - English meaning (when available)
    """
    try:
        analyzer = JapaneseAnalyzer.get_instance()
        tokens = analyzer.analyze(request.text)

        response_tokens = []
        for t in tokens:
            # Create simplified meaning text (first definition, max 30 chars)
            raw_meaning = t.meaning or ""
            # Take first definition only
            first_def = raw_meaning.split(";")[0].strip()
            
            if len(first_def) > 30:
                meaning_text = first_def[:30] + "..."
            else:
                meaning_text = first_def
            
            response_tokens.append(
                TokenResponse(
                    word=t.surface,
                    base=t.base_form,
                    reading=t.reading,
                    pos=t.pos,
                    meaning=t.meaning,
                )
            )

        return AnalyzeResponse(
            tokens=response_tokens,
            count=len(tokens),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@app.post("/analyze_simple", response_model=dict[str, str], tags=["Analysis"])
async def analyze_simple(request: AnalyzeRequest) -> dict[str, str]:
    """
    Analyze Japanese text and return vocabulary-focused results.
    
    Filters out grammar words (particles, auxiliaries) and common verbs like する.
    Returns only content words: Nouns, Verbs, Adjectives, Adjectival Nouns.
    
    Returns:
        {"result": "日本語（にほんご）= Japanese language\\n..."}
    """
    import jaconv
    from sudachipy import SplitMode
    
    # POS categories to KEEP (vocabulary words)
    POS_WHITELIST = frozenset({"名詞", "動詞", "形容詞", "形状詞"})
    
    # Helper to check if a character is hiragana
    def is_hiragana(char: str) -> bool:
        return '\u3040' <= char <= '\u309f'
    
    try:
        analyzer = JapaneseAnalyzer.get_instance()
        tokenizer = analyzer._tokenizer
        jmdict = analyzer._jmdict
        
        lines: list[str] = []
        seen_bases: set[str] = set()
        
        for m in tokenizer.tokenize(request.text, SplitMode.C):
            # === Filter 1: POS Whitelist ===
            pos_tuple = m.part_of_speech()
            main_pos = pos_tuple[0] if pos_tuple else ""
            
            if main_pos not in POS_WHITELIST:
                continue  # Skip particles, auxiliaries, suffixes, pronouns, etc.
            
            surface = m.surface()
            base_form = m.dictionary_form()
            
            # === Filter 2: "Garbage" Single Hiragana Verb Filter ===
            if main_pos == "動詞" and len(surface) == 1 and is_hiragana(surface):
                continue  # Skip fragments like い, し, れ
            
            # === Filter 3: "Suru" Filter ===
            if base_form == "する":
                continue  # Skip the common "to do" verb
            
            # === Deduplication ===
            if base_form in seen_bases:
                continue
            seen_bases.add(base_form)
            
            # === Convert reading to Hiragana ===
            reading = jaconv.kata2hira(m.reading_form())
            
            # === Lookup meaning ===
            meaning = jmdict.lookup(base_form) or ""
            if len(meaning) > 30:
                meaning_text = meaning[:30] + "..."
            else:
                meaning_text = meaning
            
            # === Format: Pipe Style ===
            lines.append(f"{surface} ({reading}) = {meaning_text}")
        
        return {"result": "\n".join(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@app.post("/tokenize", tags=["Debug"])
async def tokenize_raw(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Raw Sudachi tokenization output for debugging/learning.
    
    Shows exactly how Sudachi breaks down the text, including all POS info.
    
    Returns:
        {"tokens": [{"surface": "食べ", "dictionary_form": "食べる", "reading": "タベ", "pos": [...], ...}]}
    """
    from sudachipy import SplitMode
    
    try:
        analyzer = JapaneseAnalyzer.get_instance()
        tokenizer = analyzer._tokenizer
        
        tokens = []
        lines = []
        for m in tokenizer.tokenize(request.text, SplitMode.C):
            pos_list = list(m.part_of_speech())
            tokens.append({
                "surface": m.surface(),
                "dictionary_form": m.dictionary_form(),
                "reading": m.reading_form(),
                "normalized_form": m.normalized_form(),
                "pos": pos_list,
                "is_oov": m.is_oov(),
            })
            # Easy-to-read line: surface -> dict_form [POS0-POS1] reading
            pos_short = "-".join([p for p in pos_list[:2] if p != "*"])
            lines.append(f"{m.surface()} -> {m.dictionary_form()} [{pos_short}] {m.reading_form()}")
        
        return {"tokens": tokens, "count": len(tokens), "result": "\n".join(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tokenization failed: {e!s}") from e


@app.post("/analyze_full", response_model=dict[str, str], tags=["Analysis"])
async def analyze_full(request: AnalyzeRequest) -> dict[str, str]:
    """
    Full analysis including ALL tokens (grammar words, particles, auxiliaries).
    
    Unlike /analyze_simple, this does NOT filter out grammar.
    Useful for studying sentence structure.
    
    Returns:
        {"result": "日本語 (にほんご) [Noun] = Japanese\\nを [Particle]\\n..."}
    """
    import jaconv
    from sudachipy import SplitMode
    
    # POS mapping to English
    POS_MAP = {
        "名詞": "Noun",
        "動詞": "Verb",
        "形容詞": "Adj",
        "形状詞": "Na-Adj",
        "副詞": "Adverb",
        "助詞": "Particle",
        "助動詞": "Aux",
        "接続詞": "Conj",
        "連体詞": "Adnominal",
        "感動詞": "Interj",
        "接頭辞": "Prefix",
        "接尾辞": "Suffix",
        "代名詞": "Pronoun",
        "補助記号": "Punct",
        "記号": "Symbol",
    }
    
    # Grammar explanations for particles and auxiliaries
    GRAMMAR_MAP = {
        # Particles (助詞)
        "は": "topic marker",
        "が": "subject marker",
        "を": "object marker",
        "に": "direction/time/target",
        "で": "location/means",
        "の": "possessive/of",
        "と": "and/with/quote",
        "も": "also/too",
        "から": "from/because",
        "まで": "until/to",
        "へ": "toward",
        "より": "than/from",
        "か": "question/or",
        "ね": "isn't it?",
        "よ": "emphasis",
        "な": "don't!/attributive",
        "わ": "feminine emphasis",
        "ぞ": "strong emphasis",
        "さ": "filler/emphasis",
        "て": "connection/request",
        "で": "by means of",
        "けど": "but/although",
        "けれど": "but/although",
        "けれども": "but/although",
        "のに": "despite/although",
        "ので": "because/so",
        "たり": "doing things like",
        "ながら": "while doing",
        "ばかり": "only/just",
        "だけ": "only/just",
        "しか": "only (with neg)",
        "ほど": "extent/degree",
        "くらい": "about/approximately",
        "など": "etc./and so on",
        "こそ": "emphasis (this very)",
        "さえ": "even",
        "すら": "even",
        "でも": "but/even",
        "とも": "both/even if",
        "やら": "or/what with",
        "なら": "if/as for",
        "たら": "if/when",
        "ば": "if/when",
        "って": "quotation (casual)",
        # Auxiliaries (助動詞)
        "ます": "polite form",
        "です": "copula (polite)",
        "だ": "copula (plain)",
        "た": "past tense",
        "ない": "negation",
        "ぬ": "negation (archaic)",
        "れる": "passive/potential",
        "られる": "passive/potential",
        "せる": "causative",
        "させる": "causative",
        "たい": "want to",
        "たがる": "seems to want",
        "そう": "seems like",
        "よう": "manner/let's",
        "らしい": "seems/apparently",
        "べき": "should",
        "はず": "expected to",
        "まい": "won't/probably not",
        "う": "volitional",
        "よう": "volitional",
        # Pronouns (代名詞)
        "私": "I/me",
        "僕": "I (male)",
        "俺": "I (rough male)",
        "あなた": "you",
        "君": "you (familiar)",
        "彼": "he/him",
        "彼女": "she/her",
        "これ": "this",
        "それ": "that",
        "あれ": "that (over there)",
        "ここ": "here",
        "そこ": "there",
        "あそこ": "over there",
        "誰": "who",
        "何": "what",
        "どこ": "where",
        "いつ": "when",
        "どう": "how",
        "なぜ": "why",
        "どれ": "which",
    }
    
    try:
        analyzer = JapaneseAnalyzer.get_instance()
        tokenizer = analyzer._tokenizer
        jmdict = analyzer._jmdict
        
        lines: list[str] = []
        seen_bases: set[str] = set()
        
        for m in tokenizer.tokenize(request.text, SplitMode.C):
            pos_tuple = m.part_of_speech()
            main_pos = pos_tuple[0] if pos_tuple else ""
            
            # Skip punctuation and symbols
            if main_pos in {"補助記号", "記号", "空白"}:
                continue
            
            surface = m.surface()
            base_form = m.dictionary_form()
            reading = jaconv.kata2hira(m.reading_form())
            pos_english = POS_MAP.get(main_pos, main_pos)
            
            # Deduplication
            if base_form in seen_bases:
                continue
            seen_bases.add(base_form)
            
            # Get meaning based on word type
            meaning_text = ""
            
            # Check grammar map first (for particles, auxiliaries, pronouns)
            if base_form in GRAMMAR_MAP:
                meaning_text = GRAMMAR_MAP[base_form]
            elif surface in GRAMMAR_MAP:
                meaning_text = GRAMMAR_MAP[surface]
            # Lookup in JMDict for content words
            elif main_pos in {"名詞", "動詞", "形容詞", "形状詞", "副詞"}:
                meaning = jmdict.lookup(base_form) or ""
                if len(meaning) > 25:
                    meaning_text = meaning[:25] + "..."
                else:
                    meaning_text = meaning
            
            # Format output
            if meaning_text:
                line = f"{surface} ({reading}) [{pos_english}] = {meaning_text}"
            else:
                line = f"{surface} ({reading}) [{pos_english}]"
            
            lines.append(line)
        
        return {"result": "\n".join(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e





# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
