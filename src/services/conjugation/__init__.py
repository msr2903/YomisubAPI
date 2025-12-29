"""
Conjugation service package - handles verb/adjective conjugation logic and analysis.

This package provides:
- Data constants (GRAMMAR_MAP, POS_MAP, etc.)
- Phrase pattern matching (COMPOUND_PHRASES, try_match_compound_phrase)
- Helper functions (build_conjugation_info, try_deconjugate_verb)
- Analysis functions (analyze_text, analyze_simple, analyze_full)

Usage:
    from services.conjugation import analyze_full, GRAMMAR_MAP
"""

# Import from submodules for clean API
from .data import (
    AUXILIARY_DESCRIPTIONS,
    CONJUGATION_DESCRIPTIONS,
    GRAMMAR_MAP,
    POS_MAP,
    POS_WHITELIST,
    SKIP_POS,
)

from .phrases import (
    ENDING_CONJUGATIONS,
    PHRASE_BASES,
    COMPOUND_PHRASES,
    try_match_compound_phrase,
)

from .helpers import (
    get_auxiliary_info,
    get_conjugation_info,
    is_verb_type2,
    is_hiragana,
    make_past_tense,
    build_conjugation_info,
    generate_translation_hint,
    try_deconjugate_verb,
    can_attach_morpheme,
)

# Import analysis functions from the new analysis module
from services.analysis import (
    analyze_text,
    analyze_simple,
    analyze_full,
    deconjugate_word,
    conjugate_word,
    tokenize_raw,
)

# Re-export enums from verb module for convenience
from services.verb import Conjugation, Auxiliary

__all__ = [
    # Data
    "AUXILIARY_DESCRIPTIONS",
    "CONJUGATION_DESCRIPTIONS", 
    "GRAMMAR_MAP",
    "POS_MAP",
    "POS_WHITELIST",
    "SKIP_POS",
    # Phrases
    "ENDING_CONJUGATIONS",
    "PHRASE_BASES",
    "COMPOUND_PHRASES",
    "try_match_compound_phrase",
    # Helpers
    "get_auxiliary_info",
    "get_conjugation_info",
    "is_verb_type2",
    "is_hiragana",
    "make_past_tense",
    "build_conjugation_info",
    "generate_translation_hint",
    "try_deconjugate_verb",
    "can_attach_morpheme",
    # Analysis functions
    "analyze_text",
    "analyze_simple",
    "analyze_full",
    "deconjugate_word",
    "conjugate_word",
    "tokenize_raw",
    # Enums
    "Conjugation",
    "Auxiliary",
]
