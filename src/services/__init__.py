"""Yomisub services module."""

from .analyzer import JapaneseAnalyzer
from .adjective import (
    AdjConjugation,
    AdjDeconjugated,
    conjugate_adjective,
    deconjugate_adjective,
    get_adjective_stem,
    identify_adjective_type,
)
from .verb import (
    Conjugation,
    Auxiliary,
    VerbDeconjugated,
    conjugate,
    conjugate_auxiliaries,
    deconjugate_verb,
    identify_verb_type,
)

__all__ = [
    # Analyzer
    "JapaneseAnalyzer",
    # Adjective conjugation
    "AdjConjugation",
    "AdjDeconjugated", 
    "conjugate_adjective",
    "deconjugate_adjective",
    "get_adjective_stem",
    "identify_adjective_type",
    # Verb conjugation
    "Conjugation",
    "Auxiliary",
    "VerbDeconjugated",
    "conjugate",
    "conjugate_auxiliaries",
    "deconjugate_verb",
    "identify_verb_type",
]
