"""Phrase pattern matching system for grammar expressions."""

# =============================================================================
# Compositional Phrase Matching System
# =============================================================================
# Instead of hardcoding every variant (ない, ません, なかった, ませんでした),
# we define base patterns and automatically generate all conjugation variants.

# Conjugatable endings and their variants
# Format: (base_ending, [(variant, suffix_label), ...])
ENDING_CONJUGATIONS = {
    # ない (i-adjective negative) conjugations
    "ない": [
        ("ない", ""),
        ("ません", " (polite)"),
        ("なかった", " (past)"),
        ("ませんでした", " (polite past)"),
        ("なくて", " (te-form)"),
    ],
    # できる (ichidan verb) conjugations
    "できる": [
        ("できる", ""),
        ("できます", " (polite)"),
        ("できない", " (negative)"),
        ("できません", " (polite negative)"),
        ("できた", " (past)"),
        ("できました", " (polite past)"),
        ("できなかった", " (negative past)"),
    ],
    # ある (godan verb) conjugations
    "ある": [
        ("ある", ""),
        ("あります", " (polite)"),
        ("あった", " (past)"),
        ("ありました", " (polite past)"),
        ("ない", " (negative)"),  # ある→ない special
        ("ありません", " (polite negative)"),
    ],
    # いる (ichidan verb) conjugations
    "いる": [
        ("いる", ""),
        ("います", " (polite)"),
        ("いた", " (past)"),
        ("いました", " (polite past)"),
        ("いない", " (negative)"),
        ("いません", " (polite negative)"),
    ],
    # なる (godan verb) conjugations
    "なる": [
        ("なる", ""),
        ("なります", " (polite)"),
        ("なった", " (past)"),
        ("ならない", " (negative)"),
        ("なりません", " (polite negative)"),
    ],
    # する (irregular) conjugations
    "する": [
        ("する", ""),
        ("します", " (polite)"),
        ("した", " (past)"),
        ("しない", " (negative)"),
        ("しません", " (polite negative)"),
    ],
    # いい/よい (i-adjective) conjugations
    "いい": [
        ("いい", ""),
        ("いいです", " (polite)"),
        ("よかった", " (past)"),
        ("よくない", " (negative)"),
    ],
    # だ (copula) conjugations
    "だ": [
        ("だ", ""),
        ("です", " (polite)"),
        ("だった", " (past)"),
        ("でした", " (polite past)"),
        ("ではない", " (negative)"),
        ("じゃない", " (negative casual)"),
    ],
    # いける/いけない pattern
    "いけない": [
        ("いけない", ""),
        ("いけません", " (polite)"),
        ("だめ", " (casual)"),
    ],
}

# Base patterns: (stem, ending_type, base_meaning)
# The stem is the fixed part, ending_type refers to ENDING_CONJUGATIONS
PHRASE_BASES = [
    # かも patterns
    ("かもしれ", "ない", "might; may; possibly"),
    
    # こと patterns
    ("ことが", "できる", "can; be able to"),
    ("ことが", "ある", "sometimes; have experienced"),
    ("ことに", "する", "decide to"),
    ("ことに", "なる", "it's been decided; will end up"),
    ("ことは", "ない", "no need to; never happens"),
    
    # はず patterns
    ("はず", "だ", "should be; expected to"),
    ("はずが", "ない", "can't be; impossible"),
    
    # わけ patterns
    ("わけが", "ない", "no way that; impossible"),
    ("わけでは", "ない", "doesn't mean that"),
    ("わけにはいか", "ない", "can't possibly; mustn't"),
    
    # べき patterns
    ("べき", "だ", "should; ought to"),
    ("べきでは", "ない", "should not"),
    
    # つもり patterns
    ("つもり", "だ", "intend to; plan to"),
    
    # ほうが patterns
    ("ほうが", "いい", "had better; should"),
    
    # て form patterns
    ("ては", "いけない", "must not; may not"),
    ("ても", "いい", "may; it's okay to"),
    
    # に patterns  
    ("にちがい", "ない", "must be; no doubt"),
    ("にすぎ", "ない", "merely; nothing but"),
    ("とは限ら", "ない", "not necessarily; not always"),
]


def _generate_compound_phrases():
    """Generate all phrase variants from base patterns."""
    result = {}
    
    # Generate from compositional patterns
    for stem, ending_type, base_meaning in PHRASE_BASES:
        if ending_type not in ENDING_CONJUGATIONS:
            continue
        
        for variant, suffix in ENDING_CONJUGATIONS[ending_type]:
            full_phrase = stem + variant
            meaning = base_meaning + suffix
            
            # Get first character as key
            first_char = full_phrase[0]
            if first_char not in result:
                result[first_char] = []
            result[first_char].append((full_phrase, meaning))
    
    return result


# Generate the compositional phrases
_COMPOSITIONAL_PHRASES = _generate_compound_phrases()

# Multi-token grammar phrases that should be grouped together
# Key: first token, Value: list of (full_phrase, meaning)
# Organized by JLPT level patterns
COMPOUND_PHRASES = {
    # === か patterns ===
    "か": [
        ("かどうか", "whether or not"),
        ("かのように", "as if; as though"),
    ],
    # === こと patterns (N5-N4) ===
    "こと": [
        ("ことにする", "decide to"),
        ("ことになる", "it's been decided; will end up"),
    ],
    # === な patterns ===
    "な": [
        ("なければならない", "must; have to"),
        ("なければいけない", "must; have to"),
        ("なければなりません", "must (polite)"),
        ("なくてはならない", "must; have to"),
        ("なくてはいけない", "must; have to"),
        ("ないといけない", "must; have to"),
        ("なきゃ", "must (casual)"),
        ("なくちゃ", "must (casual)"),
        ("ないわけにはいかない", "must; have no choice but to"),
    ],
    # === なきゃ patterns ===
    "なきゃ": [
        ("なきゃいけない", "must; have to (casual)"),
        ("なきゃだめ", "must; have to (casual)"),
        ("なきゃならない", "must; have to (casual)"),
    ],
    # === なくちゃ patterns ===
    "なくちゃ": [
        ("なくちゃいけない", "must; have to (casual)"),
        ("なくちゃだめ", "must; have to (casual)"),
        ("なくちゃならない", "must; have to (casual)"),
    ],
    # === と patterns ===
    "と": [
        ("といけない", "must (if not...)"),
        ("といけません", "must (polite)"),
        ("とだめ", "must; no good if not"),
        ("というのは", "what ~ means is"),
        ("ということだ", "it means that; I heard that"),
        ("というものだ", "that's what ~ is"),
        ("というわけだ", "that's why; so that means"),
        ("ところだ", "about to; just did"),
        ("ところだった", "was about to"),
    ],
    # === て patterns ===
    "て": [
        ("てはいけない", "must not; may not"),
        ("てはいけません", "must not (polite)"),
        ("てはだめ", "must not (casual)"),
        ("てもいいですか", "may I...?"),
        ("ても", "even if; even though"),
        ("てからでないと", "not until after"),
        ("てたまらない", "unbearably; extremely"),
        ("てならない", "can't help but feel"),
        ("てばかりいる", "do nothing but"),
    ],
    # === ては patterns ===
    "ては": [
        ("てはだめ", "must not (casual)"),
    ],
    # === は patterns ===
    "は": [
        ("はいけない", "must not"),
        ("はいけません", "must not (polite)"),
        ("はだめ", "must not (casual)"),
    ],
    # === はず patterns (auto-generated have priority) ===
    "はず": [],
    # === ほう patterns ===
    "ほう": [],
    # === ほど patterns ===
    "ほど": [
        ("ほど", "the more... the more"),
    ],
    # === も patterns ===
    "も": [
        ("もいいですか", "may I...?"),
    ],
    # === わけ patterns ===
    "わけ": [
        ("わけだ", "no wonder; that's why"),
    ],
    # === べ patterns ===
    "べ": [],
    # === つもり patterns ===
    "つもり": [],
    # === ば patterns ===
    "ば": [
        ("ばよかった", "should have; wish I had"),
        ("ばいい", "should; ought to"),
        ("ばいいのに", "I wish; if only"),
        ("ばかり", "just; only; nothing but"),
        ("ばかりだ", "just did; only getting more"),
        ("ばかりでなく", "not only... but also"),
    ],
    # === た patterns ===
    "た": [
        ("たばかり", "just did"),
        ("たことがある", "have done before"),
        ("たことがない", "have never done"),
        ("たほうがいい", "had better"),
        ("たらいい", "should; would be good if"),
        ("たらどう", "how about; why don't you"),
    ],
    # === に patterns ===
    "に": [
        ("において", "in; at; regarding"),
        ("に対して", "towards; regarding"),
        ("について", "about; concerning"),
        ("によって", "by means of; depending on"),
        ("にとって", "for; to (someone)"),
        ("にしても", "even if; even though"),
        ("にしては", "for; considering"),
        ("に関して", "regarding; concerning"),
        ("に比べて", "compared to"),
        ("につれて", "as; in proportion to"),
        ("に従って", "in accordance with"),
    ],
    # === の patterns ===
    "の": [
        ("のに", "although; even though"),
        ("ので", "because; since"),
        ("のだ", "it is that; the fact is"),
        ("のです", "it is that (polite)"),
        ("のではない", "it's not that"),
    ],
    # === そ patterns ===
    "そ": [
        ("そうだ", "I heard that; seems like"),
        ("そうです", "I heard that (polite)"),
        ("そうにない", "unlikely to; doesn't seem"),
        ("そうもない", "no sign of; unlikely"),
    ],
    # === よ patterns ===
    "よ": [
        ("ようにする", "to make sure to"),
        ("ようになる", "to come to; to become able"),
        ("ようとする", "try to; be about to"),
        ("ようがない", "no way to; cannot"),
        ("ようとしない", "refuses to; won't try to"),
    ],
    # === ざ patterns ===
    "ざ": [
        ("ざるをえない", "can't help but; have to"),
    ],
    # === し patterns ===
    "し": [
        ("しかない", "have no choice but to"),
        ("しかたがない", "can't be helped"),
        ("しかたない", "can't be helped (casual)"),
    ],
    # === せ patterns ===
    "せ": [
        ("せいだ", "because of (negative cause)"),
        ("せいで", "because of (negative cause)"),
    ],
    # === お patterns ===
    "お": [
        ("おかげだ", "thanks to (positive cause)"),
        ("おかげで", "thanks to (positive cause)"),
    ],
    # === ど patterns ===
    "ど": [
        ("どころか", "far from; let alone"),
        ("どころではない", "not in a position to"),
    ],
    # === き patterns ===
    "き": [
        ("きり", "only; since"),
        ("きりがない", "endless; no end to"),
    ],
    # === だ patterns ===
    "だ": [
        ("だけでなく", "not only... but also"),
        ("だけでは", "just... is not enough"),
        ("だろう", "probably; I think"),
    ],
    # === ちゃ patterns (casual contractions) ===
    "ちゃ": [
        ("ちゃう", "end up doing (casual)"),
        ("ちゃった", "ended up doing"),
        ("ちゃいけない", "must not (casual)"),
        ("ちゃだめ", "must not (casual)"),
    ],
    # === じゃ patterns ===
    "じゃ": [
        ("じゃない", "isn't; not"),
        ("じゃないですか", "isn't it?"),
        ("じゃん", "isn't it? (casual)"),
    ],
    # === らしい patterns ===
    "らしい": [
        ("らしい", "seems like; apparently"),
        ("らしいです", "seems like (polite)"),
    ],
    # === みたい patterns ===
    "みたい": [
        ("みたいだ", "seems like; looks like"),
        ("みたいです", "seems like (polite)"),
        ("みたいに", "like; as if"),
        ("みたいな", "like (adj)"),
    ],
    # === っぽい patterns ===
    "っぽい": [
        ("っぽい", "-ish; -like; tends to"),
    ],
    # === ため patterns ===
    "ため": [
        ("ために", "in order to; for the sake of"),
        ("ためだ", "because of; for"),
    ],
    # === よう patterns (additional) ===
    "よう": [
        ("ような", "like; such as"),
        ("ように", "so that; in order to"),
        ("ようだ", "seems like; appears"),
        ("ようです", "seems like (polite)"),
    ],
    # === とおり patterns ===
    "とおり": [
        ("とおりに", "as; in accordance with"),
        ("とおりだ", "it's just as"),
    ],
    # === かわり patterns ===
    "かわり": [
        ("かわりに", "instead of; in exchange for"),
    ],
    # === たび patterns ===
    "たび": [
        ("たびに", "every time; whenever"),
    ],
    # === うち patterns ===
    "うち": [
        ("うちに", "while; before"),
        ("うちは", "while; as long as"),
    ],
    # === あいだ patterns ===
    "あいだ": [
        ("あいだに", "while; during"),
        ("あいだは", "during the time"),
    ],
    # === かぎり patterns ===
    "かぎり": [
        ("かぎり", "as long as; to the extent"),
        ("かぎりでは", "as far as"),
    ],
    # === ところ patterns ===
    "ところ": [
        ("ところで", "by the way"),
        ("ところだ", "about to; just did"),
        ("ところだった", "was about to"),
    ],
    # === すぎ patterns ===
    "すぎ": [
        ("すぎる", "too much; excessively"),
        ("すぎた", "was too much"),
    ],
    # === やすい patterns ===
    "やすい": [
        ("やすい", "easy to do"),
        ("やすかった", "was easy to do"),
    ],
    # === にくい patterns ===
    "にくい": [
        ("にくい", "hard to do; difficult to"),
        ("にくかった", "was hard to do"),
    ],
    # === はじめ patterns ===
    "はじめ": [
        ("はじめる", "start doing"),
        ("はじめた", "started doing"),
    ],
    # === おわり patterns ===
    "おわり": [
        ("おわる", "finish doing"),
        ("おわった", "finished doing"),
    ],
    # === つづけ patterns ===
    "つづけ": [
        ("つづける", "continue doing"),
        ("つづけた", "continued doing"),
    ],
    # === がち patterns ===
    "がち": [
        ("がちだ", "tend to; prone to"),
        ("がちな", "tending to (adj)"),
    ],
    # === 気味 patterns ===
    "気味": [
        ("気味だ", "a touch of; slightly"),
        ("気味で", "feeling somewhat"),
    ],
    # =========================================================================
    # Auxiliary Verb Patterns (attach to masu-stem)
    # =========================================================================
    "かけ": [
        ("かける", "start doing; partially do"),
        ("かけだ", "in the middle of doing"),
        ("かけた", "started doing; was about to"),
    ],
    "かね": [
        ("かねる", "cannot (polite); hesitate to"),
        ("かねない", "might; could possibly (negative)"),
        ("かねます", "cannot (polite)"),
    ],
    "きる": [
        ("きる", "do completely; finish"),
        ("きった", "finished completely"),
        ("きれる", "can do completely"),
        ("きれない", "cannot finish; unbearable"),
        ("きれなかった", "couldn't finish"),
    ],
    "きれ": [
        ("きれる", "can do completely"),
        ("きれない", "cannot finish; unbearable"),
    ],
    "こむ": [
        ("こむ", "do thoroughly; go into"),
        ("こんだ", "did thoroughly"),
    ],
    "こめ": [
        ("こめる", "put into (feelings/effort)"),
        ("こめた", "put into"),
    ],
    "だす": [
        ("だす", "start doing (sudden); burst out"),
        ("だした", "burst out doing"),
    ],
    "なおす": [
        ("なおす", "do over; correct; fix"),
        ("なおした", "did over; fixed"),
    ],
    "ながら": [
        ("ながら", "while doing; although"),
    ],
    "がたい": [
        ("がたい", "hard to (psychologically)"),
        ("がたかった", "was hard to"),
    ],
    "がる": [
        ("がる", "act like; show signs of"),
        ("がった", "acted like"),
        ("がっている", "is showing signs of"),
    ],
    "ず": [
        ("ずに", "without doing"),
        ("ずにはいられない", "can't help but"),
        ("ずにはおかない", "cannot leave without"),
    ],
    "づらい": [
        ("づらい", "hard to (physical/habitual)"),
        ("づらかった", "was hard to"),
    ],
    "てる": [
        ("てる", "is doing (casual)"),
        ("てた", "was doing (casual)"),
        ("てない", "not doing (casual)"),
    ],
    "とく": [
        ("とく", "do in advance (casual)"),
        ("といた", "did in advance (casual)"),
        ("とけ", "do in advance! (casual imperative)"),
    ],
    "まま": [
        ("まま", "as is; in the state of"),
        ("ままだ", "is still in the state of"),
        ("ままで", "while remaining"),
    ],
    "まい": [
        ("まい", "will not; probably not"),
        ("まいと", "trying not to"),
    ],
    "まで": [
        ("までだ", "only; just; that's all"),
        ("までのことだ", "that's all there is to it"),
    ],
    "くせ": [
        ("くせに", "although; despite (critical)"),
        ("くせして", "despite (critical)"),
    ],
    "くらい": [
        ("くらい", "about; at least; to the extent"),
        ("ぐらい", "about; at least"),
    ],
    "うる": [
        ("うる", "possible (formal)"),
        ("うべき", "should (formal)"),
    ],
    "える": [
        ("える", "possible (formal)"),
        ("えない", "impossible (formal)"),
    ],
    "あげ": [
        ("あげる", "do for someone (give up)"),
        ("あげた", "did for someone"),
    ],
    "もらう": [
        ("もらう", "have someone do (receive)"),
        ("もらった", "had someone do"),
        ("もらえる", "can have someone do"),
    ],
    "くれ": [
        ("くれる", "do for me (give)"),
        ("くれた", "did for me"),
        ("くれない", "won't do for me"),
    ],
    "みせ": [
        ("みせる", "I'll show you I can..."),
        ("みせた", "showed I could"),
    ],
    "として": [
        ("としても", "assuming; even if"),
        ("としては", "as for; considering"),
    ],
}

# Merge compositional phrases into COMPOUND_PHRASES
# This adds auto-generated variants like かもしれません from かもしれ + ない pattern
for first_char, phrase_list in _COMPOSITIONAL_PHRASES.items():
    if first_char not in COMPOUND_PHRASES:
        COMPOUND_PHRASES[first_char] = []
    # Add compositional phrases (avoid duplicates)
    existing = {p[0] for p in COMPOUND_PHRASES[first_char]}
    for phrase, meaning in phrase_list:
        if phrase not in existing:
            COMPOUND_PHRASES[first_char].append((phrase, meaning))

# Sort all phrase lists by length (descending) for greedy matching
for key in COMPOUND_PHRASES:
    COMPOUND_PHRASES[key] = sorted(COMPOUND_PHRASES[key], key=lambda x: -len(x[0]))


def try_match_compound_phrase(morphemes: list, start_idx: int) -> tuple[str, str, int] | None:
    """
    Try to match a compound phrase starting at start_idx.
    Returns (phrase, meaning, tokens_consumed) or None.
    """
    if start_idx >= len(morphemes):
        return None
    
    first_surface = morphemes[start_idx].surface()
    
    # Check both the full first surface AND just the first character
    # (compositional phrases use first character as key)
    candidates = []
    if first_surface in COMPOUND_PHRASES:
        candidates.extend(COMPOUND_PHRASES[first_surface])
    first_char = first_surface[0] if first_surface else ""
    if first_char in COMPOUND_PHRASES and first_char != first_surface:
        candidates.extend(COMPOUND_PHRASES[first_char])
    
    if not candidates:
        return None
    
    # Build the remaining text from morphemes
    remaining = "".join(m.surface() for m in morphemes[start_idx:start_idx + 10])
    
    # Check each possible phrase (longest first for greedy match)
    for phrase, meaning in sorted(candidates, key=lambda x: -len(x[0])):
        if remaining.startswith(phrase):
            # Count how many tokens this phrase consumes
            consumed = 0
            chars_matched = 0
            for m in morphemes[start_idx:]:
                if chars_matched >= len(phrase):
                    break
                chars_matched += len(m.surface())
                consumed += 1
            return (phrase, meaning, consumed)
    
    return None
