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
    components: list["TokenInfo"] | None = None  # Parts of a conjugated token

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
        tokens: list[TokenInfo] = []
        seen_bases: set[str] = set()
        
        # Buffer to hold morphemes for the current group
        group_buffer: list[Morpheme] = []
        
        def flush_buffer():
            if not group_buffer:
                return

            # Analyze the group
            head = group_buffer[0]
            tail = group_buffer[1:]
            
            # Helper to create TokenInfo from a morpheme
            def make_token(m: Morpheme) -> TokenInfo:
                s = m.surface()
                b = m.dictionary_form()
                r_kata = m.reading_form()
                r = jaconv.kata2hira(r_kata)
                p = self._extract_pos(m)
                mn = self._lookup_meaning(b, s)
                if not mn and self._is_katakana(s):
                    mn = None # Ensure consistent logic for cleanup
                return TokenInfo(s, b, r, p, mn)

            head_token = make_token(head)
            
            # If it's a single token, just emit it (unless it was filtered proper noun)
            if not tail:
                # Proper noun filter check 
                # (Note: Original logic was: if not meaning and is_katakana: continue)
                # We replicate that here.
                if not head_token.meaning and self._is_katakana(head_token.surface):
                    group_buffer.clear()
                    return

                # Deduplication logic (original used seen_bases)
                # We apply dedupe on the HEAD's base form for the main list
                if head_token.base_form not in seen_bases:
                    seen_bases.add(head_token.base_form)
                    tokens.append(head_token)
            else:
                # It is a group!
                # 1. Create the Surface Form (concatenated)
                full_surface = "".join(m.surface() for m in group_buffer)
                
                # 2. Components
                component_tokens = [make_token(m) for m in group_buffer]
                
                # 3. Create the compound token
                # Base form is the HEAD's base form.
                # POS is the HEAD's POS (usually Verb).
                # Meaning is HEAD's meaning.
                # We add 'components' list.
                
                compound_token = TokenInfo(
                    surface=full_surface,
                    base_form=head_token.base_form,
                    reading="".join(c.reading for c in component_tokens), # Concatenate readings
                    pos=head_token.pos,
                    meaning=head_token.meaning,
                    components=component_tokens
                )
                
                # Deduplicate based on HEAD base form
                if head_token.base_form not in seen_bases:
                    seen_bases.add(head_token.base_form)
                    tokens.append(compound_token)
            
            group_buffer.clear()

        # Iterate and Group
        raw_morphemes = self._tokenizer.tokenize(text, split_mode)
        
        for morpheme in raw_morphemes:
            pos_tuple = morpheme.part_of_speech()
            main_pos = pos_tuple[0]
            sub_pos1 = pos_tuple[1]
            
            # Skip punctuation/symbols globally?
            # Original: if main_pos in self.SKIP_POS: continue
            # If inside a group, we probably shouldn't skip?
            # Actually punctuation breaks a group usually.
            if main_pos in self.SKIP_POS:
                flush_buffer()
                continue

            # Determine if this morpheme can extend the current group
            # Conditions to be a TAIL:
            # 1. Auxiliary (助動詞)
            # 2. Suffix (接尾辞)
            # 3. Non-independent Verb/Adj (非自立可能) 
            #    e.g. ている (いる), ておく (おく), てほしい (ほしい)
            # 4. Conjunctive Particle (接続助詞) - e.g. て, ば, 
            #    But be careful: "から" (cause/from) is also 接続助詞 sometimes? 
            #    Yes: 食べたから (because I ate).
            #    Do we want "Eat because"? Maybe not.
            #    Strict conjugation usually includes て (Te), ば (Ba), たら (Tara), たり (Tari).
            #    Let's limit particles to safely connective ones if possible.
            #    Sudachi labels: 接続助詞.
            
            is_tail_candidate = (
                main_pos in {"助動詞", "接尾辞"} or
                sub_pos1 == "非自立可能" or
                (main_pos == "助詞" and sub_pos1 == "接続助詞")
            )
            
            # However, a group must START with a Predicate (Verb/Adj/Na-Adj).
            # If buffer is empty, this must be a Head.
            
            if not group_buffer:
                # Starting a new potential group
                # Must be Verb/Adj/Na-Adj (and NOT Non-independent if we want to be strict heads)
                # But sometimes a sentence starts with non-independent? Unlikely for "Base Meaning".
                # Let's accept any non-symbol as head, but we only GROUP if head is Predicate.
                group_buffer.append(morpheme)
            else:
                # Buffer has content. Can we attach?
                # We only attach if the HEAD (group_buffer[0]) is a Predicate (Verb/Adj/Shape).
                # And the current is a valid Tail.
                
                head_pos = group_buffer[0].part_of_speech()
                head_main = head_pos[0]
                
                is_predicate_head = head_main in {"動詞", "形容詞", "形状詞"}
                
                # Refine Tail Logic:
                # Don't attach "Specific Particles" like "から" (because)?
                # "て" is surface "て" (or "で").
                # "ば" is surface "ば".
                # "たり" is surface "たり".
                # "ながら" (while) -> Eat-while? Maybe group.
                # "つつ" (while) -> Group.
                # "けど" (but) -> Eat-but? No.
                # "ので" (so) -> Eat-so? No.
                
                attach = False
                if is_predicate_head and is_tail_candidate:
                    # Filter specific particles if needed
                    if main_pos == "助詞":
                        # Allow: て, で, ば, たり, だら (tara?), ながら, つつ
                        # Disallow: から, けれど, のに, ので, し
                        # Simple whitelist of surfaces?
                        s = morpheme.surface()
                        if s in {"て", "で", "ば", "たり", "だら", "たら", "なら", "ながら", "つつ"}: 
                            attach = True
                        else:
                            attach = False
                    else:
                        attach = True # Aux, Suffix, Non-Indep are always attached
                
                if attach:
                    group_buffer.append(morpheme)
                else:
                    # Cannot attach to current group.
                    flush_buffer()
                    # Start new group with current
                    group_buffer.append(morpheme)
        
        # Flush remaining
        flush_buffer()

        return tokens

    @staticmethod
    def _is_katakana(text: str) -> bool:
        """Check if text is primarily katakana (likely a name/loanword)."""
        if not text:
            return False
        katakana_count = sum(1 for c in text if '\u30a0' <= c <= '\u30ff')
        return katakana_count / len(text) > 0.5

