"""Yomisub FastAPI application - Japanese text analysis API."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from models import (
    AnalyzeRequest,
    DeconjugateRequest,
    ConjugateRequest,
    AnalyzeResponse,
    SimpleAnalyzeResponse,
    FullAnalyzeResponse,
    DeconjugateResponse,
    ConjugateResponse,
)
from services.analyzer import JapaneseAnalyzer
from services.analysis import (
    analyze_text,
    analyze_simple,
    analyze_full,
    deconjugate_word,
    conjugate_word,
    tokenize_raw,
)


# ============================================================================
# Application Lifespan
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize heavy resources on startup."""
    _ = JapaneseAnalyzer.get_instance()
    yield


# ============================================================================
# FastAPI Application
# ============================================================================


app = FastAPI(
    title="Yomisub API",
    description="""Japanese text analysis API for language learning.

## Features
- **Tokenization**: Break Japanese text into words
- **Readings**: Get hiragana readings for all words  
- **Definitions**: English meanings from JMDict
- **Conjugation Analysis**: Understand verb/adjective forms
- **Deconjugation**: Break down complex forms like 食べられなかった

## Endpoints
- `/analyze` - Full structured analysis
- `/analyze_simple` - Vocabulary-focused (no grammar words)
- `/analyze_full` - All tokens with grammar explanations
- `/deconjugate` - Deep analysis of single conjugated word
- `/conjugate` - Generate conjugations from dictionary form
""",
    version="0.2.0",
    lifespan=lifespan,
)


# ============================================================================
# Middleware & Static Files
# ============================================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/interface", include_in_schema=False)
async def interface():
    """Serve the analyzer interface."""
    return FileResponse(BASE_DIR / "static" / "index.html")


# ============================================================================
# Health Endpoints
# ============================================================================


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "yomisub", "version": "0.2.0"}


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Detailed health check."""
    return {"status": "healthy", "version": "0.2.0"}


# ============================================================================
# Analysis Endpoints
# ============================================================================


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_endpoint(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze Japanese text and return structured token information.

    Returns tokens with:
    - Surface form, base form, reading, POS
    - English meaning
    - Conjugation breakdown for verbs/adjectives
    - Component tokens for compound words
    """
    try:
        return analyze_text(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@app.post("/analyze_simple", response_model=SimpleAnalyzeResponse, tags=["Analysis"])
async def analyze_simple_endpoint(request: AnalyzeRequest) -> SimpleAnalyzeResponse:
    """
    Vocabulary-focused analysis. Filters out grammar words.
    
    Returns only content words (nouns, verbs, adjectives) with:
    - Dictionary form and reading
    - English meaning
    - Conjugation hint for verbs/adjectives
    """
    try:
        return analyze_simple(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@app.post("/analyze_full", response_model=FullAnalyzeResponse, tags=["Analysis"])
async def analyze_full_endpoint(request: AnalyzeRequest) -> FullAnalyzeResponse:
    """
    Full analysis including ALL tokens with grammar explanations.
    
    Includes particles, auxiliaries, and complete conjugation breakdowns.
    Best for studying sentence structure.
    """
    try:
        return analyze_full(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


# ============================================================================
# Conjugation Endpoints
# ============================================================================


@app.post("/deconjugate", response_model=DeconjugateResponse, tags=["Conjugation"])
async def deconjugate_endpoint(request: DeconjugateRequest) -> DeconjugateResponse:
    """
    Deep analysis of a conjugated word.
    
    Breaks down complex forms like 食べられなかった into their components
    and explains each layer of conjugation.
    """
    try:
        return deconjugate_word(
            word=request.word,
            dictionary_form=request.dictionary_form,
            word_type=request.word_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deconjugation failed: {e!s}") from e


@app.post("/conjugate", response_model=ConjugateResponse, tags=["Conjugation"])
async def conjugate_endpoint(request: ConjugateRequest) -> ConjugateResponse:
    """
    Generate conjugations from a dictionary form.
    
    Specify which forms you want, or get all common forms.
    """
    try:
        return conjugate_word(
            word=request.word,
            word_type=request.word_type,
            requested_forms=request.forms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conjugation failed: {e!s}") from e


# ============================================================================
# Debug Endpoints
# ============================================================================


@app.post("/tokenize", tags=["Debug"])
async def tokenize_endpoint(request: AnalyzeRequest) -> dict[str, Any]:
    """Raw Sudachi tokenization output for debugging."""
    try:
        return tokenize_raw(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tokenization failed: {e!s}") from e


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
