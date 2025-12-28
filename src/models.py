"""Pydantic models for Yomisub API requests and responses."""

from pydantic import BaseModel, Field
from typing import Literal


# ============================================================================
# Request Models
# ============================================================================


class AnalyzeRequest(BaseModel):
    """Request body for text analysis."""
    text: str = Field(..., min_length=1, max_length=10000, description="Japanese text to analyze")


class DeconjugateRequest(BaseModel):
    """Request body for deconjugation."""
    word: str = Field(..., min_length=1, max_length=100, description="Conjugated word to analyze")
    dictionary_form: str | None = Field(None, description="Dictionary form (optional, will try to detect)")
    word_type: Literal["verb", "adjective", "auto"] = Field("auto", description="Word type")


class ConjugateRequest(BaseModel):
    """Request body for conjugation."""
    word: str = Field(..., min_length=1, max_length=50, description="Dictionary form")
    word_type: Literal["verb", "i-adjective", "na-adjective"] = Field(..., description="Word type")
    forms: list[str] | None = Field(None, description="Specific forms to generate (optional)")


# ============================================================================
# Response Components
# ============================================================================


class ConjugationLayer(BaseModel):
    """Single layer in a conjugation chain."""
    form: str = Field(..., description="The conjugated form segment")
    type: str = Field(..., description="Type (auxiliary or conjugation)")
    english: str = Field(..., description="English name")
    meaning: str = Field(..., description="What it adds to the meaning")


class ConjugationInfo(BaseModel):
    """Full conjugation breakdown."""
    chain: list[ConjugationLayer] = Field(default_factory=list, description="Conjugation layers")
    summary: str = Field("", description="Brief summary like 'passive + negative + past'")
    translation_hint: str = Field("", description="Suggested English translation")


class TokenComponent(BaseModel):
    """Component of a compound token."""
    surface: str = Field(..., description="Surface form")
    base: str = Field(..., description="Dictionary form")
    reading: str = Field(..., description="Reading in hiragana")
    pos: str = Field(..., description="Part of speech")
    meaning: str | None = Field(None, description="Meaning or grammar role")


class TokenResponse(BaseModel):
    """Single token in analysis response."""
    word: str = Field(..., description="Surface form (as written)")
    base: str = Field(..., description="Dictionary/base form")
    reading: str = Field(..., description="Reading in hiragana")
    pos: str = Field(..., description="Part of speech")
    meaning: str | None = Field(None, description="English meaning")
    components: list[TokenComponent] | None = Field(None, description="Component tokens")
    conjugation: ConjugationInfo | None = Field(None, description="Conjugation breakdown")


class VocabularyItem(BaseModel):
    """Single vocabulary item for simple analysis."""
    word: str = Field(..., description="Surface form")
    base: str = Field(..., description="Dictionary form")
    reading: str = Field(..., description="Reading in hiragana")
    meaning: str = Field(..., description="English meaning")
    conjugation_hint: str | None = Field(None, description="How the word is conjugated")


class PhraseToken(BaseModel):
    """Token in full analysis with grammar details."""
    surface: str = Field(..., description="Surface form")
    base: str = Field(..., description="Dictionary form")
    reading: str = Field(..., description="Reading in hiragana")
    pos: str = Field(..., description="Part of speech (English)")
    meaning: str | None = Field(None, description="English meaning")
    grammar_note: str | None = Field(None, description="Grammar explanation")
    conjugation: ConjugationInfo | None = Field(None, description="Conjugation details")


# ============================================================================
# Response Models
# ============================================================================


class AnalyzeResponse(BaseModel):
    """Response body for text analysis."""
    tokens: list[TokenResponse]
    count: int = Field(..., description="Number of tokens found")


class SimpleAnalyzeResponse(BaseModel):
    """Response for /analyze_simple."""
    vocabulary: list[VocabularyItem]
    count: int
    text_result: str = Field(..., description="Human-readable text format")


class FullAnalyzeResponse(BaseModel):
    """Response for /analyze_full."""
    phrases: list[PhraseToken]
    count: int
    text_result: str = Field(..., description="Human-readable text format")


class DeconjugateResponse(BaseModel):
    """Response for /deconjugate."""
    word: str = Field(..., description="Input conjugated word")
    dictionary_form: str = Field(..., description="Dictionary form")
    word_type: str = Field(..., description="verb or adjective")
    meaning: str | None = Field(None, description="English meaning")
    layers: list[ConjugationLayer] = Field(default_factory=list)
    full_breakdown: str = Field(..., description="Summary of all conjugations")
    natural_english: str = Field("", description="Natural English hint")
    alternatives: list[dict] | None = Field(None, description="Alternative interpretations")


class ConjugateResponse(BaseModel):
    """Response for /conjugate."""
    word: str = Field(..., description="Dictionary form")
    word_type: str = Field(..., description="Word type")
    conjugations: dict[str, list[str]] = Field(..., description="Form -> conjugated words")
