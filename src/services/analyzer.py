"""Japanese text analyzer service using SudachiPy and JMDict."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Self

import jaconv
from sudachipy import Dictionary, Morpheme, SplitMode

from services.jmdict import JMDictionary


@dataclass(frozen=True, slots=True)
class TokenInfo:
    """Represents analyzed information for a single token."""

    surface: str
    base_form: str
    reading: str
    pos: str
    meaning: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for JSON serialization."""
        return {
            "word": self.surface,
            "base": self.base_form,
            "reading": self.reading,
            "pos": self.pos,
            "meaning": self.meaning,
        }


class JapaneseAnalyzer:
    """Analyzes Japanese text using SudachiPy tokenization and JMDict definitions."""

    # POS tags to skip (punctuation, symbols only - NOT grammar)
    SKIP_POS = frozenset({"補助記号", "記号", "空白"})

    # Map generic Japanese POS tags to friendly English names
    POS_MAPPING = {
        "名詞": "Noun",
        "動詞": "Verb",
        "形容詞": "Adjective",
        "副詞": "Adverb",
        "連体詞": "Determiner",
        "接続詞": "Conjunction",
        "感動詞": "Interjection",
        "助動詞": "Auxiliary",
        "助詞": "Particle",
        "接頭辞": "Prefix",
        "接尾辞": "Suffix",
        "代名詞": "Pronoun",
    }

    # Grammar explanations for particles, auxiliaries, and pronouns
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
        "けど": "but/although",
        "けれど": "but/although",
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
        "でも": "but/even",
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

    def __init__(self) -> None:
        """Initialize the analyzer with SudachiPy dictionary and JMDict."""
        self._tokenizer = Dictionary(dict="full").create()
        self._jmdict = JMDictionary.get_instance()

    @classmethod
    @lru_cache(maxsize=1)
    def get_instance(cls) -> Self:
        """Get or create a singleton instance (cached for performance)."""
        return cls()

    def _extract_pos(self, morpheme: Morpheme) -> str:
        """Extract a clean, mapped English part-of-speech string."""
        pos_tuple = morpheme.part_of_speech()
        main_category = pos_tuple[0]

        # Return mapped English POS, or fall back to the original Japanese category
        return self.POS_MAPPING.get(main_category, main_category)

    def _lookup_meaning(self, word: str, surface: str = "") -> str | None:
        """Look up English meaning for a Japanese word."""
        # Check grammar map first
        if word in self.GRAMMAR_MAP:
            return self.GRAMMAR_MAP[word]
        if surface and surface in self.GRAMMAR_MAP:
            return self.GRAMMAR_MAP[surface]
        # Fall back to JMDict
        return self._jmdict.lookup(word)

    def analyze(self, text: str, split_mode: SplitMode = SplitMode.A) -> list[TokenInfo]:
        """
        Analyze Japanese text and return token information.

        Args:
            text: Japanese text to analyze.
            split_mode: SudachiPy split mode (A=short, B=middle, C=long/named entity).

        Returns:
            List of TokenInfo objects with surface, base, reading, POS, and meaning.
        """
        if not text or not text.strip():
            return []

        tokens: list[TokenInfo] = []
        seen_bases: set[str] = set()  # Avoid duplicate base forms

        for morpheme in self._tokenizer.tokenize(text, split_mode):
            # Get the main POS category
            pos_parts = morpheme.part_of_speech()
            main_pos = pos_parts[0] if pos_parts else ""

            # Skip punctuation and symbols only
            if main_pos in self.SKIP_POS:
                continue

            surface = morpheme.surface()
            base_form = morpheme.dictionary_form()
            
            # Convert Katakana reading to Hiragana
            reading_kata = morpheme.reading_form()
            reading = jaconv.kata2hira(reading_kata)

            # Skip if we've already seen this base form
            if base_form in seen_bases:
                continue
            seen_bases.add(base_form)

            # Get the part of speech string (mapped to English)
            pos = self._extract_pos(morpheme)

            # Look up meaning (includes grammar explanations)
            meaning = self._lookup_meaning(base_form, surface)

            # Skip untranslated katakana words (likely proper nouns/names)
            if not meaning and self._is_katakana(surface):
                continue

            tokens.append(
                TokenInfo(
                    surface=surface,
                    base_form=base_form,
                    reading=reading,
                    pos=pos,
                    meaning=meaning,
                )
            )

        return tokens

    @staticmethod
    def _is_katakana(text: str) -> bool:
        """Check if text is primarily katakana (likely a name/loanword)."""
        if not text:
            return False
        katakana_count = sum(1 for c in text if '\u30a0' <= c <= '\u30ff')
        return katakana_count / len(text) > 0.5

