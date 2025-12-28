"""Conjugation service - handles verb/adjective conjugation logic and analysis."""

import jaconv
from sudachipy import SplitMode
from lemminflect import getInflection

from services.analyzer import JapaneseAnalyzer
from services.verb import (
    Conjugation,
    Auxiliary,
    conjugate,
    conjugate_auxiliaries,
    deconjugate_verb,
)
from services.adjective import (
    AdjConjugation,
    conjugate_adjective,
    deconjugate_adjective,
)
from models import (
    ConjugationLayer,
    ConjugationInfo,
    TokenComponent,
    TokenResponse,
    VocabularyItem,
    PhraseToken,
    AnalyzeResponse,
    SimpleAnalyzeResponse,
    FullAnalyzeResponse,
    DeconjugateResponse,
    ConjugateResponse,
)


# ============================================================================
# Constants
# ============================================================================

# Mapping from Auxiliary enum to human-readable descriptions
AUXILIARY_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "POTENTIAL": ("potential", "can/able to"),
    "MASU": ("polite", "polite form"),
    "NAI": ("negative", "not"),
    "TAI": ("desiderative", "want to"),
    "TAGARU": ("desiderative", "seems to want"),
    "HOSHII": ("desiderative", "want someone to"),
    "RASHII": ("evidential", "apparently"),
    "SOUDA_HEARSAY": ("hearsay", "I heard that"),
    "SOUDA_CONJECTURE": ("conjecture", "looks like"),
    "SERU_SASERU": ("causative", "make/let do"),
    "SHORTENED_CAUSATIVE": ("causative", "make/let do"),
    "RERU_RARERU": ("passive/potential", "is done/can do"),
    "CAUSATIVE_PASSIVE": ("causative-passive", "is made to do"),
    "SHORTENED_CAUSATIVE_PASSIVE": ("causative-passive", "is made to do"),
    "AGERU": ("benefactive", "do for someone"),
    "SASHIAGERU": ("benefactive-humble", "humbly do for"),
    "YARU": ("benefactive-casual", "do for (casual)"),
    "MORAU": ("receptive", "have done for me"),
    "ITADAKU": ("receptive-humble", "humbly receive"),
    "KURERU": ("benefactive-to-me", "do for me"),
    "KUDASARU": ("benefactive-humble", "kindly do for me"),
    "TE_IRU": ("progressive/resultative", "is doing/has done"),
    "TE_ARU": ("resultative", "has been done"),
    "MIRU": ("tentative", "try doing"),
    "IKU": ("directional", "go on doing"),
    "KURU": ("directional", "come to do"),
    "OKU": ("preparatory", "do in advance"),
    "SHIMAU": ("completive", "end up doing"),
    "TE_ORU": ("progressive-humble", "is doing (humble)"),
    # New auxiliaries
    "SUGIRU": ("excessive", "too much"),
    "YASUI": ("ease", "easy to"),
    "NIKUI": ("difficulty", "hard to"),
    "HAJIMERU": ("inchoative", "start doing"),
    "OWARU": ("terminative", "finish doing"),
    "TSUZUKERU": ("continuative", "continue doing"),
    "DASU": ("sudden", "burst into"),
    "GARU": ("appearance", "seems to want"),
    "SOU_APPEARANCE": ("appearance", "looks like"),
}

# Mapping from Conjugation enum to descriptions
CONJUGATION_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "NEGATIVE": ("negative", "not"),
    "CONJUNCTIVE": ("masu-stem", "connective"),
    "DICTIONARY": ("dictionary", "plain present"),
    "CONDITIONAL": ("conditional", "if/when"),
    "IMPERATIVE": ("imperative", "command"),
    "VOLITIONAL": ("volitional", "let's/will"),
    "TE": ("te-form", "and/request"),
    "TA": ("past", "did"),
    "TARA": ("conditional-past", "if/when"),
    "TARI": ("representative", "things like"),
    "ZU": ("classical-negative", "without"),
    "NU": ("classical-negative", "not"),
}

# Past tense is now handled by lemminflect library (see make_past_tense function)

# Grammar explanations for particles, auxiliaries, pronouns
GRAMMAR_MAP = {
    # Particles
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
    # Auxiliaries
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
    # Pronouns
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

# POS mapping to English
POS_MAP = {
    "名詞": "Noun",
    "動詞": "Verb",
    "形容詞": "i-Adj",
    "形状詞": "na-Adj",
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

# POS whitelist for simple analysis
POS_WHITELIST = frozenset({"名詞", "動詞", "形容詞", "形状詞"})

# POS to skip
SKIP_POS = frozenset({"補助記号", "記号", "空白"})

# Multi-token grammar phrases that should be grouped together
# Key: first token, Value: list of (full_phrase, meaning)
# Organized by JLPT level patterns
COMPOUND_PHRASES = {
    # === か patterns ===
    "か": [
        ("かもしれない", "might; may; possibly"),
        ("かもしれません", "might; may; possibly (polite)"),
        ("かどうか", "whether or not"),
        ("かのように", "as if; as though"),
    ],
    # === こと patterns (N5-N4) ===
    "こと": [
        ("ことができる", "can; be able to"),
        ("ことができます", "can (polite)"),
        ("ことがある", "sometimes; have experienced"),
        ("ことがあります", "sometimes (polite)"),
        ("ことにする", "decide to"),
        ("ことになる", "it's been decided; will end up"),
        ("ことはない", "no need to; never happens"),
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
    # === なきゃ patterns (Sudachi tokenizes as single) ===
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
        ("とは限らない", "not necessarily; not always"),
        ("ところだ", "about to; just did"),
        ("ところだった", "was about to"),
    ],
    # === て patterns ===
    "て": [
        ("てはいけない", "must not; may not"),
        ("てはいけません", "must not (polite)"),
        ("てはだめ", "must not (casual)"),
        ("てもいい", "may; it's okay to"),
        ("てもいいですか", "may I...?"),
        ("ても", "even if; even though"),
        ("てからでないと", "not until after"),
        ("てたまらない", "unbearably; extremely"),
        ("てならない", "can't help but feel"),
        ("てばかりいる", "do nothing but"),
    ],
    # === ては patterns (Sudachi tokenizes as single) ===
    "ては": [
        ("てはいけない", "must not; may not"),
        ("てはいけません", "must not (polite)"),
        ("てはだめ", "must not (casual)"),
    ],
    # === は patterns ===
    "は": [
        ("はいけない", "must not"),
        ("はいけません", "must not (polite)"),
        ("はだめ", "must not (casual)"),
    ],
    # === はず patterns ===
    "はず": [
        ("はずだ", "should be; expected to"),
        ("はずです", "should be (polite)"),
        ("はずがない", "can't be; impossible"),
    ],
    # === ほう patterns ===
    "ほう": [
        ("ほうがいい", "had better; should"),
        ("ほうがいいです", "had better (polite)"),
    ],
    # === ほど patterns ===
    "ほど": [
        ("ほど", "the more... the more"),
    ],
    # === も patterns ===
    "も": [
        ("もいい", "it's okay to"),
        ("もいいですか", "may I...?"),
    ],
    # === わけ patterns ===
    "わけ": [
        ("わけがない", "no way that; impossible"),
        ("わけではない", "doesn't mean that; not necessarily"),
        ("わけにはいかない", "can't possibly; mustn't"),
        ("わけだ", "no wonder; that's why"),
    ],
    # === べ patterns ===
    "べ": [
        ("べきだ", "should; ought to"),
        ("べきです", "should (polite)"),
        ("べきではない", "should not"),
    ],
    # === つもり patterns ===
    "つもり": [
        ("つもりだ", "intend to; plan to"),
        ("つもりです", "intend to (polite)"),
    ],
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
        ("にちがいない", "must be; no doubt"),
        ("において", "in; at; regarding"),
        ("に対して", "towards; regarding"),
        ("について", "about; concerning"),
        ("によって", "by means of; depending on"),
        ("にとって", "for; to (someone)"),
        ("にすぎない", "merely; nothing but; only"),
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
    # === かける/かねる patterns ===
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
    # === きる patterns (complete action) ===
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
    # === こむ patterns (thorough action) ===
    "こむ": [
        ("こむ", "do thoroughly; go into"),
        ("こんだ", "did thoroughly"),
    ],
    "こめ": [
        ("こめる", "put into (feelings/effort)"),
        ("こめた", "put into"),
    ],
    # === だす patterns (sudden start) ===
    "だす": [
        ("だす", "start doing (sudden); burst out"),
        ("だした", "burst out doing"),
    ],
    # === なおす patterns (redo) ===
    "なおす": [
        ("なおす", "do over; correct; fix"),
        ("なおした", "did over; fixed"),
    ],
    # === ながら patterns ===
    "ながら": [
        ("ながら", "while doing; although"),
    ],
    # === がたい patterns (psychological difficulty) ===
    "がたい": [
        ("がたい", "hard to (psychologically)"),
        ("がたかった", "was hard to"),
    ],
    # === がる patterns (show signs of) ===
    "がる": [
        ("がる", "act like; show signs of"),
        ("がった", "acted like"),
        ("がっている", "is showing signs of"),
    ],
    # === ずに patterns (without doing) ===
    "ず": [
        ("ずに", "without doing"),
        ("ずにはいられない", "can't help but"),
        ("ずにはおかない", "cannot leave without"),
    ],
    # === づらい patterns (physical difficulty) ===
    "づらい": [
        ("づらい", "hard to (physical/habitual)"),
        ("づらかった", "was hard to"),
    ],
    # === てる/てた patterns (casual progressive) ===
    "てる": [
        ("てる", "is doing (casual)"),
        ("てた", "was doing (casual)"),
        ("てない", "not doing (casual)"),
    ],
    # === とく patterns (casual preparatory) ===
    "とく": [
        ("とく", "do in advance (casual)"),
        ("といた", "did in advance (casual)"),
        ("とけ", "do in advance! (casual imperative)"),
    ],
    # === まま patterns ===
    "まま": [
        ("まま", "as is; in the state of"),
        ("ままだ", "is still in the state of"),
        ("ままで", "while remaining"),
    ],
    # === まい patterns (negative volition) ===
    "まい": [
        ("まい", "will not; probably not"),
        ("まいと", "trying not to"),
    ],
    # === までだ patterns ===
    "まで": [
        ("までだ", "only; just; that's all"),
        ("までのことだ", "that's all there is to it"),
    ],
    # === くせに patterns ===
    "くせ": [
        ("くせに", "although; despite (critical)"),
        ("くせして", "despite (critical)"),
    ],
    # === くらい patterns ===
    "くらい": [
        ("くらい", "about; at least; to the extent"),
        ("ぐらい", "about; at least"),
    ],
    # === うる/える patterns (formal possibility) ===
    "うる": [
        ("うる", "possible (formal)"),
        ("うべき", "should (formal)"),
    ],
    "える": [
        ("える", "possible (formal)"),
        ("えない", "impossible (formal)"),
    ],
    # === あげる patterns (benefactive) ===
    "あげ": [
        ("あげる", "do for someone (give up)"),
        ("あげた", "did for someone"),
    ],
    # === もらう patterns (receptive) ===
    "もらう": [
        ("もらう", "have someone do (receive)"),
        ("もらった", "had someone do"),
        ("もらえる", "can have someone do"),
    ],
    # === くれる patterns (benefactive to speaker) ===
    "くれ": [
        ("くれる", "do for me (give)"),
        ("くれた", "did for me"),
        ("くれない", "won't do for me"),
    ],
    # === みせる patterns (show ability) ===
    "みせ": [
        ("みせる", "I'll show you I can..."),
        ("みせた", "showed I could"),
    ],
    # === としても patterns ===
    "として": [
        ("としても", "assuming; even if"),
        ("としては", "as for; considering"),
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_auxiliary_info(aux: Auxiliary) -> tuple[str, str]:
    """Get (short_name, meaning) for an auxiliary."""
    return AUXILIARY_DESCRIPTIONS.get(aux.name, (aux.name.lower(), ""))


def get_conjugation_info(conj: Conjugation) -> tuple[str, str]:
    """Get (short_name, meaning) for a conjugation."""
    return CONJUGATION_DESCRIPTIONS.get(conj.name, (conj.name.lower(), ""))


def is_verb_type2(pos_tuple: tuple) -> bool:
    """Determine if a verb is Type II (ichidan) from POS info."""
    for p in pos_tuple:
        if "一段" in str(p) or "上一段" in str(p) or "下一段" in str(p):
            return True
    return False


def is_hiragana(char: str) -> bool:
    """Check if a character is hiragana."""
    return '\u3040' <= char <= '\u309f'


def make_past_tense(verb: str) -> str:
    """
    Convert English verb to past tense using lemminflect library.
    
    Uses Penn Treebank tag 'VBD' for simple past tense.
    Falls back to simple -ed rule if lemminflect fails.
    """
    verb = verb.lower().strip()
    
    # Handle verb phrases like "to eat" or "not eat"
    if verb.startswith("to "):
        base = verb[3:].split()[0] if verb[3:] else verb
        return _inflect_past(base)
    
    if verb.startswith("not "):
        base = verb[4:].split()[0] if verb[4:] else verb
        return f"didn't {base}"
    
    # Extract first word (the main verb)
    first_word = verb.split()[0]
    return _inflect_past(first_word)


def _inflect_past(verb: str) -> str:
    """Use lemminflect to get past tense form."""
    try:
        # VBD = past tense verb in Penn Treebank tags
        result = getInflection(verb, tag='VBD')
        if result:
            return result[0]
    except Exception:
        pass
    
    # Fallback to simple rules if lemminflect fails
    return _make_regular_past(verb)


def _make_regular_past(verb: str) -> str:
    """Fallback: apply regular past tense rules."""
    if verb.endswith("e"):
        return verb + "d"
    elif verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ied"
    else:
        return verb + "ed"


def try_match_compound_phrase(morphemes: list, start_idx: int) -> tuple[str, str, int] | None:
    """
    Try to match a compound phrase starting at start_idx.
    Returns (phrase, meaning, tokens_consumed) or None.
    """
    if start_idx >= len(morphemes):
        return None
    
    first_surface = morphemes[start_idx].surface()
    if first_surface not in COMPOUND_PHRASES:
        return None
    
    # Build the remaining text from morphemes
    remaining = "".join(m.surface() for m in morphemes[start_idx:start_idx + 10])
    
    # Check each possible phrase (longest first for greedy match)
    for phrase, meaning in sorted(COMPOUND_PHRASES[first_surface], key=lambda x: -len(x[0])):
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


def build_conjugation_info(
    auxiliaries: tuple[Auxiliary, ...],
    conjugation: Conjugation,
    base_meaning: str = "",
) -> ConjugationInfo:
    """Build a ConjugationInfo from deconjugation results."""
    layers: list[ConjugationLayer] = []
    summary_parts: list[str] = []
    
    for aux in auxiliaries:
        short_name, meaning = get_auxiliary_info(aux)
        layers.append(ConjugationLayer(
            form="",
            type=aux.name,
            english=short_name,
            meaning=meaning,
        ))
        summary_parts.append(short_name)
    
    conj_short, conj_meaning = get_conjugation_info(conjugation)
    if conjugation != Conjugation.DICTIONARY:
        layers.append(ConjugationLayer(
            form="",
            type=conjugation.name,
            english=conj_short,
            meaning=conj_meaning,
        ))
        summary_parts.append(conj_short)
    
    return ConjugationInfo(
        chain=layers,
        summary=" + ".join(summary_parts) if summary_parts else "dictionary form",
        translation_hint="",
    )


def generate_translation_hint(
    base_meaning: str,
    auxiliaries: tuple[Auxiliary, ...],
    conjugation: Conjugation,
) -> str:
    """Generate a natural English translation hint."""
    if not base_meaning:
        return ""
    
    first_meaning = base_meaning.split(";")[0].split(",")[0].strip()
    if first_meaning.startswith("to "):
        first_meaning = first_meaning[3:]
    
    hint = first_meaning
    
    for aux in auxiliaries:
        match aux:
            case Auxiliary.RERU_RARERU:
                hint = f"can {hint}" if "potential" in AUXILIARY_DESCRIPTIONS[aux.name][0] else f"is {hint}"
            case Auxiliary.NAI:
                hint = f"not {hint}"
            case Auxiliary.TAI:
                hint = f"want to {hint}"
            case Auxiliary.TE_IRU:
                hint = f"is {hint}ing"
            case Auxiliary.SERU_SASERU | Auxiliary.SHORTENED_CAUSATIVE:
                hint = f"make/let {hint}"
            case Auxiliary.MIRU:
                hint = f"try to {hint}"
            case Auxiliary.SHIMAU:
                hint = f"end up {hint}ing"
            case Auxiliary.MASU:
                pass
            case _:
                pass
    
    match conjugation:
        case Conjugation.TA:
            if hint.endswith("ing"):
                pass  # Keep -ing form for progressive
            elif "not" in hint:
                # Extract verb for proper past tense
                verb = hint.replace("not ", "").replace("can ", "")
                hint = f"didn't {verb}"
            elif "can " in hint:
                hint = f"could {hint.replace('can ', '')}"
            else:
                hint = make_past_tense(hint)
        case Conjugation.TE:
            hint = f"{hint} and..."
        case Conjugation.CONDITIONAL:
            hint = f"if {hint}"
        case Conjugation.TARA:
            if "not" in hint:
                hint = f"if not {hint.replace('not ', '')}"
            else:
                hint = f"when/if {make_past_tense(hint)}"
        case Conjugation.VOLITIONAL:
            hint = f"let's {hint}"
        case Conjugation.IMPERATIVE:
            hint = f"{hint}!"
        case _:
            pass
    
    return hint


def try_deconjugate_verb(
    surface: str,
    base_form: str,
    type2: bool,
    meaning: str = "",
) -> ConjugationInfo | None:
    """Try to deconjugate a verb and return ConjugationInfo."""
    if surface == base_form:
        return None
    
    try:
        results = deconjugate_verb(surface, base_form, type2=type2, max_aux_depth=2)
        if results:
            r = results[0]
            info = build_conjugation_info(r.auxiliaries, r.conjugation, meaning)
            info.translation_hint = generate_translation_hint(meaning, r.auxiliaries, r.conjugation)
            return info
    except Exception:
        pass
    
    return None


def can_attach_morpheme(next_main: str, next_sub: str, next_surface: str) -> bool:
    """Check if a morpheme can attach to form a compound."""
    return (
        next_main in {"助動詞", "接尾辞"} or
        next_sub == "非自立可能" or
        (next_main == "助詞" and next_sub == "接続助詞" and
         next_surface in {"て", "で", "ば", "たら", "たり", "ながら"})
    )


# ============================================================================
# Analysis Functions
# ============================================================================


def analyze_text(text: str) -> AnalyzeResponse:
    """Analyze Japanese text and return structured token information."""
    analyzer = JapaneseAnalyzer.get_instance()
    tokenizer = analyzer._tokenizer
    jmdict = analyzer._jmdict
    
    response_tokens: list[TokenResponse] = []
    seen_bases: set[str] = set()
    
    # Use SplitMode.C to keep compound nouns together (日本語, not 日本+語)
    morphemes = list(tokenizer.tokenize(text, SplitMode.C))
    i = 0
    
    while i < len(morphemes):
        m = morphemes[i]
        pos_tuple = m.part_of_speech()
        main_pos = pos_tuple[0] if pos_tuple else ""
        
        if main_pos in SKIP_POS:
            i += 1
            continue
        
        surface = m.surface()
        base_form = m.dictionary_form()
        reading = jaconv.kata2hira(m.reading_form())
        pos_english = POS_MAP.get(main_pos, main_pos)
        
        # Get base reading for lookup to disambiguate homonyms (e.g. 本: hon vs moto)
        lookup_reading = reading
        if base_form != surface or main_pos == "動詞" or main_pos == "形容詞":
             # Use the reading of the base form for dictionary lookup
             # This handles conjugated verbs where surface reading != base reading
             base_m = list(tokenizer.tokenize(base_form, SplitMode.C))
             if base_m:
                 lookup_reading = jaconv.kata2hira(base_m[0].reading_form())

        is_counter = "助数詞" in pos_tuple or (main_pos == "接尾辞" and "名詞的" in pos_tuple)
        details = jmdict.lookup_details(base_form, lookup_reading, is_counter=is_counter)
        meaning = details["meaning"] if details else None
        tags = details["tags"] if details else []
        
        if not meaning and base_form in GRAMMAR_MAP:
            meaning = GRAMMAR_MAP[base_form]
        if not meaning and surface in GRAMMAR_MAP:
            meaning = GRAMMAR_MAP[surface]
        
        # Collect compounds for verbs and na-adjectives
        components: list[TokenComponent] = []
        compound_surface = surface
        compound_reading = reading
        j = i + 1
        
        # Group verbs with their auxiliaries
        if main_pos == "動詞":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                
                if can_attach_morpheme(next_main, next_sub, next_m.surface()):
                    ns = next_m.surface()
                    nr = jaconv.kata2hira(next_m.reading_form())
                    nb = next_m.dictionary_form()
                    np = POS_MAP.get(next_main, next_main)
                    nm = GRAMMAR_MAP.get(nb) or GRAMMAR_MAP.get(ns)
                    
                    components.append(TokenComponent(
                        surface=ns, base=nb, reading=nr, pos=np, meaning=nm
                    ))
                    compound_surface += ns
                    compound_reading += nr
                    j += 1
                else:
                    break
        
        # Group na-adjectives with copula conjugations (じゃない, ではない, だった, etc.)
        elif main_pos == "形状詞":
            prev_was_de = False  # Track if previous token was で
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                ns = next_m.surface()
                
                # Attach: 助動詞 (だ, じゃ, では, etc.), 形容詞 (ない), or は after で
                can_attach = (
                    next_main in {"助動詞", "形容詞"} or
                    ns in {"じゃ", "では", "で"} or
                    (ns == "は" and prev_was_de)  # Allow は in ではない pattern
                )
                
                if can_attach:
                    nr = jaconv.kata2hira(next_m.reading_form())
                    nb = next_m.dictionary_form()
                    np = POS_MAP.get(next_main, next_main)
                    nm = GRAMMAR_MAP.get(nb) or GRAMMAR_MAP.get(ns)
                    
                    components.append(TokenComponent(
                        surface=ns, base=nb, reading=nr, pos=np, meaning=nm
                    ))
                    compound_surface += ns
                    compound_reading += nr
                    prev_was_de = (ns == "で")
                    j += 1
                else:
                    break
        
        if base_form in seen_bases:
            i = j
            continue
        seen_bases.add(base_form)
        
        conjugation_info = None
        if main_pos == "動詞" and compound_surface != base_form:
            type2 = is_verb_type2(pos_tuple)
            conjugation_info = try_deconjugate_verb(compound_surface, base_form, type2, meaning or "")
        
        if components:
            components.insert(0, TokenComponent(
                surface=surface, base=base_form, reading=reading,
                pos=pos_english, meaning=meaning
            ))
        
        response_tokens.append(TokenResponse(
            word=compound_surface,
            base=base_form,
            reading=compound_reading,
            pos=pos_english,
            meaning=meaning,
            tags=tags,
            components=components if components else None,
            conjugation=conjugation_info,
        ))
        
        i = j
    
    return AnalyzeResponse(tokens=response_tokens, count=len(response_tokens))


def analyze_simple(text: str) -> SimpleAnalyzeResponse:
    """Vocabulary-focused analysis, filtering out grammar words."""
    analyzer = JapaneseAnalyzer.get_instance()
    tokenizer = analyzer._tokenizer
    jmdict = analyzer._jmdict
    
    vocabulary: list[VocabularyItem] = []
    text_lines: list[str] = []
    seen_bases: set[str] = set()
    consumed_indices: set[int] = set()  # Track indices consumed by grouping
    
    morphemes = list(tokenizer.tokenize(text, SplitMode.C))
    i = 0
    
    while i < len(morphemes):
        # Skip already consumed morphemes
        if i in consumed_indices:
            i += 1
            continue
            
        m = morphemes[i]
        pos_tuple = m.part_of_speech()
        main_pos = pos_tuple[0] if pos_tuple else ""
        sub_pos = pos_tuple[1] if len(pos_tuple) > 1 else ""
        
        # Only include content words: nouns, verbs, na-adjectives, pronouns
        # Skip i-adjectives that are non-independent (like ない in 好きじゃない)
        # Allow content words and nominal suffixes (counters like 本, つ, 日)
        is_content_word = main_pos in {"名詞", "動詞", "形状詞", "代名詞", "副詞", "接続詞", "連体詞"}
        is_counter = (main_pos == "接尾辞" and sub_pos == "名詞的")
        
        if not is_content_word and not is_counter:
            # Exception: independent i-adjectives are OK (高い, 美しい)
            if main_pos == "形容詞" and sub_pos != "非自立可能":
                pass  # Allow it
            else:
                i += 1
                continue
        
        surface = m.surface()
        base_form = m.dictionary_form()
        
        # Normalize causative verbs to their true base form
        # Sudachi sometimes returns 読ます instead of 読む for causative forms
        if main_pos == "動詞" and (base_form.endswith("ます") or base_form.endswith("す") and len(base_form) > 2):
            # Try to find the actual base verb
            # 読ます → 読む, 書かす → 書く, 食べさす → 食べる
            if base_form.endswith("ます"):
                # 読ます → 読む (godan causative)
                potential_base = base_form[:-2] + "む"
                test_morphemes = list(tokenizer.tokenize(potential_base, SplitMode.C))
                if test_morphemes and test_morphemes[0].part_of_speech()[0] == "動詞":
                    base_form = potential_base
            elif base_form.endswith("さす") or base_form.endswith("させる"):
                # 食べさす/食べさせる → 食べる (ichidan causative)
                if base_form.endswith("させる"):
                    potential_base = base_form[:-3] + "る"
                else:
                    potential_base = base_form[:-2] + "る"
                test_morphemes = list(tokenizer.tokenize(potential_base, SplitMode.C))
                if test_morphemes and test_morphemes[0].part_of_speech()[0] == "動詞":
                    base_form = potential_base
        
        # Filter garbage verbs
        if main_pos == "動詞" and len(surface) == 1 and is_hiragana(surface):
            # Exception: keep し/す if followed by conjugation (しなければならない, etc.)
            if surface in {"し", "す"} and (i + 1) < len(morphemes):
                next_m = morphemes[i + 1]
                next_main = next_m.part_of_speech()[0] if next_m.part_of_speech() else ""
                if next_main == "助動詞":
                    pass  # Keep it for conjugation grouping
                else:
                    i += 1
                    continue
            else:
                i += 1
                continue
        if base_form == "する" and len(surface) > 1:
            # Only skip standalone する, not conjugated forms like しなければ
            i += 1
            continue
        
        # Collect compound
        compound_surface = surface
        j = i + 1
        conjugation_hint = None
        
        # Group verbs with their auxiliaries
        if main_pos == "動詞":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                
                if next_main in {"助動詞", "接尾辞"} or next_sub == "非自立可能" or \
                   (next_main == "助詞" and next_sub == "接続助詞"):
                    compound_surface += next_m.surface()
                    consumed_indices.add(j)
                    j += 1
                else:
                    break
        
        # Group na-adjectives (形状詞) with copula conjugations
        elif main_pos == "形状詞":
            prev_was_de = False
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                ns = next_m.surface()
                
                # Attach: 助動詞 (だ, じゃ), 形容詞 (ない), or は after で
                can_attach = (
                    next_main in {"助動詞", "形容詞"} or
                    ns in {"じゃ", "では", "で"} or
                    (ns == "は" and prev_was_de)
                )
                
                if can_attach:
                    compound_surface += ns
                    consumed_indices.add(j)
                    prev_was_de = (ns == "で")
                    j += 1
                else:
                    break
            
            # Generate conjugation hint for na-adjectives
            if compound_surface != base_form:
                if "じゃない" in compound_surface or "ではない" in compound_surface:
                    conjugation_hint = "negative (not)"
                elif "じゃなかった" in compound_surface or "ではなかった" in compound_surface:
                    conjugation_hint = "negative past (was not)"
                elif "だった" in compound_surface:
                    conjugation_hint = "past (was)"
        
        # Group i-adjectives (形容詞) with their conjugation (くない, かった, etc.)
        elif main_pos == "形容詞" and sub_pos != "非自立可能":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                ns = next_m.surface()
                
                # Attach: 形容詞-非自立可能 (ない), 助動詞 (た), or 助詞 (て, ば)
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                can_attach = (
                    (next_main == "形容詞" and next_sub == "非自立可能") or
                    next_main == "助動詞" or
                    ns in {"て", "ば"}
                )
                
                if can_attach:
                    compound_surface += ns
                    consumed_indices.add(j)
                    j += 1
                else:
                    break
            
            # Generate conjugation hint for i-adjectives
            if compound_surface != base_form:
                if compound_surface.endswith("くない"):
                    conjugation_hint = "negative (not)"
                elif compound_surface.endswith("くなかった") or compound_surface.endswith("なかった"):
                    conjugation_hint = "negative past (was not)"
                elif compound_surface.endswith("かった"):
                    conjugation_hint = "past (was)"
                elif compound_surface.endswith("くて"):
                    conjugation_hint = "te-form (and)"
                elif compound_surface.endswith("ければ"):
                    conjugation_hint = "conditional (if)"
        
        # Dedup
        if base_form in seen_bases:
            i = j
            continue
        seen_bases.add(base_form)
        
        # Get reading for the BASE form, not the conjugated surface
        # For conjugated words, look up the base form's reading
        if compound_surface != base_form:
            # Try to get the base form reading from dictionary lookup
            base_morphemes = list(tokenizer.tokenize(base_form, SplitMode.C))
            if base_morphemes:
                reading = jaconv.kata2hira(base_morphemes[0].reading_form())
            else:
                reading = jaconv.kata2hira(m.reading_form())
        else:
            reading = jaconv.kata2hira(m.reading_form())

        
        
        meaning = jmdict.lookup(base_form, reading, is_counter=is_counter) or ""
        
        if len(meaning) > 40:
            meaning_display = meaning[:40] + "..."
        else:
            meaning_display = meaning
        
        # Generate conjugation hint for verbs
        if main_pos == "動詞" and compound_surface != base_form:
            type2 = is_verb_type2(pos_tuple)
            info = try_deconjugate_verb(compound_surface, base_form, type2, meaning)
            if info:
                conjugation_hint = info.summary
                if info.translation_hint:
                    conjugation_hint += f" ({info.translation_hint})"
            else:
                # Fallback: detect common patterns that deconjugation might miss
                if "なきゃいけない" in compound_surface or "なきゃならない" in compound_surface:
                    conjugation_hint = "must; have to (casual)"
                elif "なくちゃいけない" in compound_surface or "なくちゃならない" in compound_surface:
                    conjugation_hint = "must; have to (casual)"
                elif compound_surface.endswith("なきゃ") or compound_surface.endswith("なくちゃ"):
                    conjugation_hint = "must (casual)"
                elif "なければならない" in compound_surface or "なければいけない" in compound_surface:
                    conjugation_hint = "must; have to"
                elif "ないといけない" in compound_surface:
                    conjugation_hint = "must; have to"
                elif "てはいけない" in compound_surface:
                    conjugation_hint = "must not; may not"
                elif "てもいい" in compound_surface:
                    conjugation_hint = "may; it's okay to"
        
        vocabulary.append(VocabularyItem(
            word=compound_surface,
            base=base_form,
            reading=reading,
            meaning=meaning_display,
            conjugation_hint=conjugation_hint,
        ))
        
        line = f"{base_form}（{reading}）= {meaning_display}"
        if conjugation_hint:
            line += f" [{conjugation_hint}]"
        text_lines.append(line)
        
        i = j
    
    return SimpleAnalyzeResponse(
        vocabulary=vocabulary,
        count=len(vocabulary),
        text_result="\n".join(text_lines),
    )


def analyze_full(text: str) -> FullAnalyzeResponse:
    """Full analysis including ALL tokens with grammar explanations."""
    analyzer = JapaneseAnalyzer.get_instance()
    tokenizer = analyzer._tokenizer
    jmdict = analyzer._jmdict
    
    phrases: list[PhraseToken] = []
    text_lines: list[str] = []
    seen_bases: set[str] = set()
    
    # Use SplitMode.C to keep compound nouns together
    morphemes = list(tokenizer.tokenize(text, SplitMode.C))
    i = 0
    
    while i < len(morphemes):
        m = morphemes[i]
        pos_tuple = m.part_of_speech()
        main_pos = pos_tuple[0] if pos_tuple else ""
        
        if main_pos in SKIP_POS:
            i += 1
            continue
        
        # Check for compound grammar phrases (かもしれない, なければならない, etc.)
        phrase_match = try_match_compound_phrase(morphemes, i)
        if phrase_match:
            phrase, phrase_meaning, tokens_consumed = phrase_match
            phrases.append(PhraseToken(
                surface=phrase,
                base=phrase,
                reading=phrase,  # It's all hiragana
                pos="Phrase",
                meaning=phrase_meaning,
                grammar_note=phrase_meaning,
                conjugation=None,
            ))
            text_lines.append(f"{phrase}（{phrase}）[Phrase] 【{phrase_meaning}】")
            i += tokens_consumed
            continue
        
        surface = m.surface()
        base_form = m.dictionary_form()
        reading = jaconv.kata2hira(m.reading_form())
        pos_english = POS_MAP.get(main_pos, main_pos)
        
        # Collect compounds
        compound_surface = surface
        compound_reading = reading
        j = i + 1
        
        # Group verbs with their auxiliaries
        if main_pos == "動詞":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                
                if can_attach_morpheme(next_main, next_sub, next_m.surface()):
                    compound_surface += next_m.surface()
                    compound_reading += jaconv.kata2hira(next_m.reading_form())
                    j += 1
                else:
                    break
        
        # Group na-adjectives with copula conjugations (じゃない, ではない, だった, etc.)
        elif main_pos == "形状詞":
            prev_was_de = False  # Track if previous token was で
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                ns = next_m.surface()
                
                # Attach: 助動詞 (だ, じゃ, では, etc.), 形容詞 (ない), or は after で
                can_attach = (
                    next_main in {"助動詞", "形容詞"} or
                    ns in {"じゃ", "では", "で"} or
                    (ns == "は" and prev_was_de)  # Allow は in ではない pattern
                )
                
                if can_attach:
                    compound_surface += ns
                    compound_reading += jaconv.kata2hira(next_m.reading_form())
                    prev_was_de = (ns == "で")
                    j += 1
                else:
                    break
        
        if base_form in seen_bases:
            i = j
            continue
        seen_bases.add(base_form)
        
        meaning = None
        grammar_note = None
        tags = []
        
        if main_pos in {"名詞", "動詞", "形容詞", "形状詞", "副詞"}:
            # Get base reading for lookup
            lookup_reading = reading
            if base_form != surface or main_pos == "動詞" or main_pos == "形容詞":
                 base_m = list(tokenizer.tokenize(base_form, SplitMode.C))
                 if base_m:
                     lookup_reading = jaconv.kata2hira(base_m[0].reading_form())
            

            
            is_counter = "助数詞" in pos_tuple or (main_pos == "接尾辞" and "名詞的" in pos_tuple)
            details = jmdict.lookup_details(base_form, lookup_reading, is_counter=is_counter)
            meaning = details["meaning"] if details else None
            tags = details["tags"] if details else []

            if meaning and len(meaning) > 30:
                meaning = meaning[:30] + "..."
        
        if base_form in GRAMMAR_MAP:
            grammar_note = GRAMMAR_MAP[base_form]
        elif surface in GRAMMAR_MAP:
            grammar_note = GRAMMAR_MAP[surface]
        
        conjugation_info = None
        if main_pos == "動詞" and compound_surface != base_form:
            type2 = is_verb_type2(pos_tuple)
            conjugation_info = try_deconjugate_verb(compound_surface, base_form, type2, meaning or "")
            
            # Fallback: detect common patterns that deconjugation might miss
            if conjugation_info is None:
                fallback_summary = None
                if "なきゃいけない" in compound_surface or "なきゃならない" in compound_surface:
                    fallback_summary = "must; have to (casual)"
                elif "なくちゃいけない" in compound_surface or "なくちゃならない" in compound_surface:
                    fallback_summary = "must; have to (casual)"
                elif compound_surface.endswith("なきゃ") or compound_surface.endswith("なくちゃ"):
                    fallback_summary = "must (casual)"
                elif "なければならない" in compound_surface or "なければいけない" in compound_surface:
                    fallback_summary = "must; have to"
                elif "ないといけない" in compound_surface:
                    fallback_summary = "must; have to"
                elif "てはいけない" in compound_surface or "ちゃいけない" in compound_surface:
                    fallback_summary = "must not; may not"
                elif "てもいい" in compound_surface:
                    fallback_summary = "may; it's okay to"
                elif "ている" in compound_surface or "てる" in compound_surface:
                    fallback_summary = "progressive/resultative"
                elif "てしまう" in compound_surface or "ちゃう" in compound_surface or "ちゃった" in compound_surface:
                    fallback_summary = "completive (end up doing)"
                elif "てみる" in compound_surface:
                    fallback_summary = "try doing"
                elif "ておく" in compound_surface or "とく" in compound_surface:
                    fallback_summary = "do in advance"
                
                if fallback_summary:
                    conjugation_info = ConjugationInfo(
                        chain=[],
                        summary=fallback_summary,
                        translation_hint=fallback_summary,
                    )
        
        phrases.append(PhraseToken(
            surface=compound_surface,
            base=base_form,
            reading=compound_reading,
            pos=pos_english,
            meaning=meaning,
            grammar_note=grammar_note,
            tags=tags,
            conjugation=conjugation_info,
        ))
        
        line = f"{compound_surface}（{compound_reading}）[{pos_english}]"
        if meaning:
            line += f" = {meaning}"
        if grammar_note:
            line += f" 【{grammar_note}】"
        if conjugation_info:
            line += f" → {conjugation_info.summary}"
        text_lines.append(line)
        
        i = j
    
    return FullAnalyzeResponse(
        phrases=phrases,
        count=len(phrases),
        text_result="\n".join(text_lines),
    )


# ============================================================================
# Deconjugation/Conjugation Functions
# ============================================================================


def deconjugate_word(
    word: str,
    dictionary_form: str | None = None,
    word_type: str = "auto",
) -> DeconjugateResponse:
    """Deep analysis of a conjugated word."""
    analyzer = JapaneseAnalyzer.get_instance()
    jmdict = analyzer._jmdict
    
    dict_form = dictionary_form
    detected_type = word_type
    
    # Try to detect dictionary form if not provided
    if not dict_form:
        tokenizer = analyzer._tokenizer
        morphemes = list(tokenizer.tokenize(word, SplitMode.A))
        if morphemes:
            dict_form = morphemes[0].dictionary_form()
            pos_tuple = morphemes[0].part_of_speech()
            main_pos = pos_tuple[0] if pos_tuple else ""
            if main_pos == "動詞":
                detected_type = "verb"
            elif main_pos == "形容詞":
                detected_type = "adjective"
    
    if not dict_form:
        raise ValueError("Could not determine dictionary form")
    
    # Get reading of the dictionary form for accurate lookup
    dict_reading = None
    if jmdict.is_loaded:
        morphemes = list(analyzer._tokenizer.tokenize(dict_form, SplitMode.C))
        if morphemes:
            dict_reading = jaconv.kata2hira(morphemes[0].reading_form())

    meaning = jmdict.lookup(dict_form, dict_reading)
    
    layers: list[ConjugationLayer] = []
    full_breakdown = ""
    natural_english = ""
    alternatives: list[dict] = []
    
    if detected_type == "verb" or detected_type == "auto":
        # Try both type1 and type2
        results = deconjugate_verb(word, dict_form, type2=True, max_aux_depth=3)
        if not results:
            results = deconjugate_verb(word, dict_form, type2=False, max_aux_depth=3)
        
        if results:
            best = results[0]
            
            for aux in best.auxiliaries:
                short_name, aux_meaning = get_auxiliary_info(aux)
                layers.append(ConjugationLayer(
                    form="",
                    type=aux.name,
                    english=short_name,
                    meaning=aux_meaning,
                ))
            
            conj_short, conj_meaning = get_conjugation_info(best.conjugation)
            if best.conjugation != Conjugation.DICTIONARY:
                layers.append(ConjugationLayer(
                    form="",
                    type=best.conjugation.name,
                    english=conj_short,
                    meaning=conj_meaning,
                ))
            
            parts = [get_auxiliary_info(a)[0] for a in best.auxiliaries]
            if best.conjugation != Conjugation.DICTIONARY:
                parts.append(conj_short)
            full_breakdown = " + ".join(parts) if parts else "dictionary form"
            
            natural_english = generate_translation_hint(meaning or "", best.auxiliaries, best.conjugation)
            
            for alt in results[1:3]:
                alt_parts = [get_auxiliary_info(a)[0] for a in alt.auxiliaries]
                alt_conj_short, _ = get_conjugation_info(alt.conjugation)
                if alt.conjugation != Conjugation.DICTIONARY:
                    alt_parts.append(alt_conj_short)
                alternatives.append({
                    "breakdown": " + ".join(alt_parts),
                    "auxiliaries": [a.name for a in alt.auxiliaries],
                    "conjugation": alt.conjugation.name,
                })
            
            detected_type = "verb"
    
    if detected_type == "adjective":
        results = deconjugate_adjective(word, dict_form, is_i_adjective=True)
        if not results:
            results = deconjugate_adjective(word, dict_form, is_i_adjective=False)
        
        if results:
            best = results[0]
            conj_name = best.conjugation.name.replace("_", " ").lower()
            layers.append(ConjugationLayer(
                form="",
                type=best.conjugation.name,
                english=conj_name,
                meaning="",
            ))
            full_breakdown = conj_name
            detected_type = "adjective"
    
    return DeconjugateResponse(
        word=word,
        dictionary_form=dict_form,
        word_type=detected_type if detected_type != "auto" else "unknown",
        meaning=meaning,
        layers=layers,
        full_breakdown=full_breakdown or "unknown form",
        natural_english=natural_english,
        alternatives=alternatives if alternatives else None,
    )


def conjugate_word(
    word: str,
    word_type: str,
    requested_forms: list[str] | None = None,
) -> ConjugateResponse:
    """Generate conjugations from a dictionary form."""
    conjugations: dict[str, list[str]] = {}
    
    if word_type == "verb":
        # Detect ichidan (type 2) vs godan (type 1) verbs
        # Ichidan verbs end in -iru or -eru (い段/え段 + る)
        # For kanji verbs, we check the reading using Sudachi
        type2 = False
        if word.endswith("る") and len(word) >= 2:
            # Try to get reading from tokenizer for accurate detection
            try:
                analyzer = JapaneseAnalyzer.get_instance()
                morphemes = list(analyzer._tokenizer.tokenize(word, SplitMode.A))
                if morphemes:
                    pos_tuple = morphemes[0].part_of_speech()
                    type2 = is_verb_type2(pos_tuple)
            except Exception:
                # Fallback: check if character before る is in i-dan or e-dan
                pre_ru = word[-2]
                type2 = pre_ru in "いきしちにひみりえけせてねへめれ"
        
        if not requested_forms:
            requested_forms = ["negative", "past", "te", "potential", "passive", "causative", "polite"]
        
        form_map = {
            "negative": (Conjugation.NEGATIVE, []),
            "past": (Conjugation.TA, []),
            "te": (Conjugation.TE, []),
            "conditional": (Conjugation.CONDITIONAL, []),
            "volitional": (Conjugation.VOLITIONAL, []),
            "imperative": (Conjugation.IMPERATIVE, []),
            "potential": (Conjugation.DICTIONARY, [Auxiliary.POTENTIAL]),
            "passive": (Conjugation.DICTIONARY, [Auxiliary.RERU_RARERU]),
            "causative": (Conjugation.DICTIONARY, [Auxiliary.SERU_SASERU]),
            "polite": (Conjugation.DICTIONARY, [Auxiliary.MASU]),
            "negative_past": (Conjugation.TA, [Auxiliary.NAI]),
            "want": (Conjugation.DICTIONARY, [Auxiliary.TAI]),
            "progressive": (Conjugation.DICTIONARY, [Auxiliary.TE_IRU]),
        }
        
        for form_name in requested_forms:
            form_key = form_name.lower().replace("-", "_").replace(" ", "_")
            if form_key in form_map:
                conj, auxs = form_map[form_key]
                try:
                    if auxs:
                        result = conjugate_auxiliaries(word, auxs, conj, type2)
                    else:
                        result = conjugate(word, conj, type2)
                    conjugations[form_name] = [r for r in result if len(r) > 1]
                except Exception:
                    conjugations[form_name] = []
    
    elif word_type == "i-adjective":
        if not requested_forms:
            requested_forms = ["negative", "past", "negative_past", "te", "adverbial"]
        
        form_map = {
            "negative": AdjConjugation.NEGATIVE,
            "past": AdjConjugation.PAST,
            "negative_past": AdjConjugation.NEGATIVE_PAST,
            "te": AdjConjugation.CONJUNCTIVE_TE,
            "adverbial": AdjConjugation.ADVERBIAL,
            "conditional": AdjConjugation.CONDITIONAL,
            "noun": AdjConjugation.NOUN,
        }
        
        for form_name in requested_forms:
            form_key = form_name.lower().replace("-", "_").replace(" ", "_")
            if form_key in form_map:
                try:
                    result = conjugate_adjective(word, form_map[form_key], is_i_adjective=True)
                    conjugations[form_name] = result
                except Exception:
                    conjugations[form_name] = []
    
    elif word_type == "na-adjective":
        if not requested_forms:
            requested_forms = ["prenominal", "negative", "past", "te", "adverbial"]
        
        form_map = {
            "prenominal": AdjConjugation.PRENOMINAL,
            "negative": AdjConjugation.NEGATIVE,
            "past": AdjConjugation.PAST,
            "negative_past": AdjConjugation.NEGATIVE_PAST,
            "te": AdjConjugation.CONJUNCTIVE_TE,
            "adverbial": AdjConjugation.ADVERBIAL,
            "conditional": AdjConjugation.CONDITIONAL,
        }
        
        for form_name in requested_forms:
            form_key = form_name.lower().replace("-", "_").replace(" ", "_")
            if form_key in form_map:
                try:
                    result = conjugate_adjective(word, form_map[form_key], is_i_adjective=False)
                    conjugations[form_name] = result
                except Exception:
                    conjugations[form_name] = []
    
    return ConjugateResponse(
        word=word,
        word_type=word_type,
        conjugations=conjugations,
    )


def tokenize_raw(text: str) -> dict:
    """Raw Sudachi tokenization output for debugging."""
    analyzer = JapaneseAnalyzer.get_instance()
    tokenizer = analyzer._tokenizer
    
    tokens = []
    lines = []
    for m in tokenizer.tokenize(text, SplitMode.C):
        pos_list = list(m.part_of_speech())
        tokens.append({
            "surface": m.surface(),
            "dictionary_form": m.dictionary_form(),
            "reading": m.reading_form(),
            "normalized_form": m.normalized_form(),
            "pos": pos_list,
            "is_oov": m.is_oov(),
        })
        pos_short = "-".join([p for p in pos_list[:2] if p != "*"])
        lines.append(f"{m.surface()} -> {m.dictionary_form()} [{pos_short}] {m.reading_form()}")
    
    return {"tokens": tokens, "count": len(tokens), "result": "\n".join(lines)}
