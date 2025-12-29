"""Analysis service - provides text analysis endpoints for the API.

This module contains the main analysis functions used by the API:
- analyze_text: Basic analysis with conjugation grouping
- analyze_simple: Vocabulary-focused analysis (filters grammar)
- analyze_full: Complete analysis including all grammar tokens
- deconjugate_word: Deep conjugation analysis
- conjugate_word: Generate conjugation forms
- tokenize_raw: Raw Sudachi output for debugging
"""

import jaconv
from sudachipy import SplitMode

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

# Import shared data and helpers from the conjugation package
# Import shared data and helpers from the conjugation package submodules
# Avoid importing from services.conjugation directly to prevent circular imports
from services.conjugation.data import (
    AUXILIARY_DESCRIPTIONS,
    CONJUGATION_DESCRIPTIONS,
    GRAMMAR_MAP,
    POS_MAP,
    POS_WHITELIST,
    SKIP_POS,
)
from services.conjugation.phrases import (
    COMPOUND_PHRASES,
    try_match_compound_phrase,
)
from services.conjugation.helpers import (
    get_auxiliary_info,
    get_conjugation_info,
    is_verb_type2,
    is_hiragana,
    build_conjugation_info,
    generate_translation_hint,
    generate_adjective_hint,
    try_deconjugate_verb,
    try_deconjugate_adjective,
    can_attach_morpheme,
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
    
    morphemes = list(tokenizer.tokenize(text, SplitMode.C))
    i = 0
    
    while i < len(morphemes):
        # Check for compound grammar phrases first (e.g. nakereba narimasen -> must)
        phrase_match = try_match_compound_phrase(morphemes, i)
        if phrase_match:
            phrase_text, phrase_meaning, consumed_count = phrase_match
            
            # Construct phrase reading from consumed tokens
            phrase_reading = ""
            for k in range(consumed_count):
                phrase_reading += jaconv.kata2hira(morphemes[i+k].reading_form())

            # Format translation hint
            # "must; have to" -> "must"
            clean_meaning = phrase_meaning.split(";")[0].strip()
            
            # Create a Phrase Token
            response_tokens.append(TokenResponse(
                word=phrase_text,
                base=phrase_text,
                reading=phrase_reading,
                pos="Phrase",
                meaning=phrase_meaning,
                tags=["Grammar"],
                components=[], 
                conjugation=ConjugationInfo(
                    chain=[ConjugationLayer(type="PHRASE", form="", english=clean_meaning, meaning=phrase_meaning)],
                    summary=clean_meaning,
                    translation_hint=clean_meaning
                )
            ))
            i += consumed_count
            continue
            
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
        
        # Get base reading for lookup
        lookup_reading = reading
        if base_form != surface or main_pos in {"動詞", "形容詞"}:
            base_m = list(tokenizer.tokenize(base_form, SplitMode.C))
            if base_m:
                lookup_reading = jaconv.kata2hira(base_m[0].reading_form())

        is_counter = "助数詞" in pos_tuple or (main_pos == "接尾辞" and "名詞的" in pos_tuple)
        details = jmdict.lookup_details(base_form, lookup_reading, is_counter=is_counter)
        meaning = details["meaning"] if details else None
        tags = details["tags"] if details else []
        
        # Check for "Ra-nuki" (colloquial potential)
        # e.g. 食べれる (tabereru) -> 食べる (taberu)
        if main_pos == "動詞" and base_form.endswith("れる") and len(base_form) > 2:
            potential_base = base_form[:-2] + "る"
            # Try correction even if meaning exists, because many ra-nuki forms are now in dictionaries
            # but we want to deconjugate them back to their root for better analysis.
            # We skip this for common non-potential verbs that happen to end in -reru.
            skip_correction = {"入れる", "忘れる", "訪れる", "触れる", "離れる", "現れる", "流れる", "溢れる", "零れる", "分かれる"}
            
            if base_form not in skip_correction:
                # Always try to find a more fundamental base verb if it ends in -reru
                ra_details = jmdict.lookup_details(potential_base) 
                if ra_details:
                    base_form = potential_base
                    meaning = ra_details["meaning"]
                    tags = ra_details["tags"]
                    # Update reading if possible
                    if lookup_reading and lookup_reading.endswith("れる"):
                        lookup_reading = lookup_reading[:-2] + "る"
        
        if not meaning:
            meaning = GRAMMAR_MAP.get(base_form) or GRAMMAR_MAP.get(surface)
        
        # Collect compound components
        components: list[TokenComponent] = []
        compound_surface = surface
        compound_reading = reading
        j = i + 1
        
        # Group verbs with auxiliaries
        if main_pos == "動詞":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                
                # Allow SOU (conjecture) which Sudachi labels as Shape/Na-adj
                is_sou = (next_m.dictionary_form() == "そう" and next_main == "形状詞")
                
                if can_attach_morpheme(next_main, next_sub, next_m.surface()) or is_sou:
                    ns, nr = next_m.surface(), jaconv.kata2hira(next_m.reading_form())
                    nb, np = next_m.dictionary_form(), POS_MAP.get(next_main, next_main)
                    nm = GRAMMAR_MAP.get(nb) or GRAMMAR_MAP.get(ns)
                    components.append(TokenComponent(surface=ns, base=nb, reading=nr, pos=np, meaning=nm))
                    compound_surface += ns
                    compound_reading += nr
                    j += 1
                else:
                    break
        
        # Group na-adjectives with copula
        elif main_pos == "形状詞":
            prev_was_de = False
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                ns = next_m.surface()
                
                can_attach = (
                    next_main in {"助動詞"} or
                    ns in {"じゃ", "では", "で"} or
                    (ns == "は" and prev_was_de)
                )
                
                if can_attach:
                    nr = jaconv.kata2hira(next_m.reading_form())
                    nb, np = next_m.dictionary_form(), POS_MAP.get(next_main, next_main)
                    nm = GRAMMAR_MAP.get(nb) or GRAMMAR_MAP.get(ns)
                    components.append(TokenComponent(surface=ns, base=nb, reading=nr, pos=np, meaning=nm))
                    compound_surface += ns
                    compound_reading += nr
                    prev_was_de = (ns == "で")
                    j += 1
                else:
                    break
        
        # Group i-adjectives with auxiliaries
        elif main_pos == "形容詞":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                ns = next_m.surface()
                
                can_attach = (
                    next_main in {"助動詞"} or
                    (next_main == "助詞" and ns in {"て", "で", "ば"})
                )
                
                if can_attach:
                    nr = jaconv.kata2hira(next_m.reading_form())
                    nb, np = next_m.dictionary_form(), POS_MAP.get(next_main, next_main)
                    nm = GRAMMAR_MAP.get(nb) or GRAMMAR_MAP.get(ns)
                    components.append(TokenComponent(surface=ns, base=nb, reading=nr, pos=np, meaning=nm))
                    compound_surface += ns
                    compound_reading += nr
                    j += 1
                else:
                    break
        
        if base_form in seen_bases:
            i = j
            continue
        seen_bases.add(base_form)
        
        # Try deconjugation for verbs
        conjugation_info = None
        if main_pos == "動詞" and compound_surface != base_form:
            type2 = is_verb_type2(pos_tuple)
            conjugation_info = try_deconjugate_verb(compound_surface, base_form, type2, meaning or "")
        elif main_pos == "形容詞" and compound_surface != base_form:
            conjugation_info = try_deconjugate_adjective(compound_surface, base_form, meaning or "")
        
        if components:
            components.insert(0, TokenComponent(
                surface=surface, base=base_form, reading=reading, pos=pos_english, meaning=meaning
            ))
        
        response_tokens.append(TokenResponse(
            word=compound_surface, base=base_form, reading=compound_reading,
            pos=pos_english, meaning=meaning, tags=tags,
            components=components if components else None, conjugation=conjugation_info,
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
    consumed_indices: set[int] = set()
    
    morphemes = list(tokenizer.tokenize(text, SplitMode.C))
    i = 0
    
    while i < len(morphemes):
        if i in consumed_indices:
            i += 1
            continue
        
        m = morphemes[i]
        pos_tuple = m.part_of_speech()
        main_pos = pos_tuple[0] if pos_tuple else ""
        sub_pos = pos_tuple[1] if len(pos_tuple) > 1 else ""
        
        # Only content words
        is_content = main_pos in {"名詞", "動詞", "形状詞", "代名詞", "副詞", "接続詞", "連体詞"}
        is_counter = (main_pos == "接尾辞" and sub_pos == "名詞的")
        
        if not is_content and not is_counter:
            if main_pos == "形容詞" and sub_pos != "非自立可能":
                pass
            else:
                i += 1
                continue
        
        surface = m.surface()
        base_form = m.dictionary_form()
        
        # Filter garbage verbs
        if main_pos == "動詞" and len(surface) == 1 and is_hiragana(surface):
            if surface in {"し", "す"} and (i + 1) < len(morphemes):
                next_m = morphemes[i + 1]
                if next_m.part_of_speech()[0] != "助動詞":
                    i += 1
                    continue
            else:
                i += 1
                continue
        if base_form == "する" and len(surface) > 1:
            i += 1
            continue
        
        # Collect compound
        compound_surface = surface
        j = i + 1
        conjugation_hint = None
        
        # Group verbs with auxiliaries
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
        
        # Group na-adjectives with copula
        elif main_pos == "形状詞":
            prev_was_de = False
            while j < len(morphemes):
                next_m = morphemes[j]
                next_main = next_m.part_of_speech()[0] if next_m.part_of_speech() else ""
                ns = next_m.surface()
                
                can_attach = next_main in {"助動詞", "形容詞"} or ns in {"じゃ", "では", "で"} or (ns == "は" and prev_was_de)
                if can_attach:
                    compound_surface += ns
                    consumed_indices.add(j)
                    prev_was_de = (ns == "で")
                    j += 1
                else:
                    break
            
            if compound_surface != base_form:
                if "じゃない" in compound_surface or "ではない" in compound_surface:
                    conjugation_hint = "negative (not)"
                elif "だった" in compound_surface:
                    conjugation_hint = "past (was)"
        
        # Group i-adjectives
        elif main_pos == "形容詞" and sub_pos != "非自立可能":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                ns = next_m.surface()
                
                can_attach = (next_main == "形容詞" and next_sub == "非自立可能") or next_main == "助動詞" or ns in {"て", "ば"}
                if can_attach:
                    compound_surface += ns
                    consumed_indices.add(j)
                    j += 1
                else:
                    break
            
            if compound_surface != base_form:
                if compound_surface.endswith("くない"):
                    conjugation_hint = "negative (not)"
                elif compound_surface.endswith("かった"):
                    conjugation_hint = "past (was)"
        
        if base_form in seen_bases:
            i = j
            continue
        seen_bases.add(base_form)
        
        # Get reading for base form
        if compound_surface != base_form:
            base_morphemes = list(tokenizer.tokenize(base_form, SplitMode.C))
            reading = jaconv.kata2hira(base_morphemes[0].reading_form()) if base_morphemes else jaconv.kata2hira(m.reading_form())
        else:
            reading = jaconv.kata2hira(m.reading_form())
        
        meaning = jmdict.lookup(base_form, reading, is_counter=is_counter) or ""
        meaning_display = meaning[:40] + "..." if len(meaning) > 40 else meaning
        
        # Generate conjugation hint for verbs
        if main_pos == "動詞" and compound_surface != base_form:
            type2 = is_verb_type2(pos_tuple)
            info = try_deconjugate_verb(compound_surface, base_form, type2, meaning)
            if info:
                conjugation_hint = f"{info.summary} ({info.translation_hint})" if info.translation_hint else info.summary
        
        vocabulary.append(VocabularyItem(
            word=compound_surface, base=base_form, reading=reading,
            meaning=meaning_display, conjugation_hint=conjugation_hint,
        ))
        
        line = f"{base_form}（{reading}）= {meaning_display}"
        if conjugation_hint:
            line += f" [{conjugation_hint}]"
        text_lines.append(line)
        i = j
    
    return SimpleAnalyzeResponse(vocabulary=vocabulary, count=len(vocabulary), text_result="\n".join(text_lines))


def analyze_full(text: str) -> FullAnalyzeResponse:
    """Full analysis including ALL tokens with grammar explanations."""
    analyzer = JapaneseAnalyzer.get_instance()
    tokenizer = analyzer._tokenizer
    jmdict = analyzer._jmdict
    
    phrases: list[PhraseToken] = []
    text_lines: list[str] = []
    seen_bases: set[str] = set()
    
    morphemes = list(tokenizer.tokenize(text, SplitMode.C))
    i = 0
    
    while i < len(morphemes):
        m = morphemes[i]
        pos_tuple = m.part_of_speech()
        main_pos = pos_tuple[0] if pos_tuple else ""
        
        if main_pos in SKIP_POS:
            i += 1
            continue
        
        # Check for compound grammar phrases
        phrase_match = try_match_compound_phrase(morphemes, i)
        if phrase_match:
            phrase, phrase_meaning, tokens_consumed = phrase_match
            phrases.append(PhraseToken(
                surface=phrase, base=phrase, reading=phrase, pos="Phrase",
                meaning=phrase_meaning, grammar_note=phrase_meaning, conjugation=None,
            ))
            text_lines.append(f"{phrase}（{phrase}）[Phrase] 【{phrase_meaning}】")
            i += tokens_consumed
            continue
        
        surface = m.surface()
        base_form = m.dictionary_form()
        reading = jaconv.kata2hira(m.reading_form())
        pos_english = POS_MAP.get(main_pos, main_pos)
        
        # Collect compounds
        compound_surface, compound_reading = surface, reading
        j = i + 1
        
        # Group verbs with auxiliaries
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
        
        # Group na-adjectives with copula
        elif main_pos == "形状詞":
            prev_was_de = False
            while j < len(morphemes):
                next_m = morphemes[j]
                next_main = next_m.part_of_speech()[0] if next_m.part_of_speech() else ""
                ns = next_m.surface()
                
                can_attach = next_main in {"助動詞", "形容詞"} or ns in {"じゃ", "では", "で"} or (ns == "は" and prev_was_de)
                if can_attach:
                    compound_surface += ns
                    compound_reading += jaconv.kata2hira(next_m.reading_form())
                    prev_was_de = (ns == "で")
                    j += 1
                else:
                    break
        
        # Group i-adjectives
        elif main_pos == "形容詞":
            while j < len(morphemes):
                next_m = morphemes[j]
                next_pos = next_m.part_of_speech()
                next_main = next_pos[0] if next_pos else ""
                next_sub = next_pos[1] if len(next_pos) > 1 else ""
                ns = next_m.surface()
                
                can_attach = (next_main == "形容詞" and next_sub == "非自立可能") or next_main == "助動詞" or ns in {"て", "ば"}
                if can_attach:
                    compound_surface += ns
                    compound_reading += jaconv.kata2hira(next_m.reading_form())
                    j += 1
                else:
                    break
        
        # Group nouns with copula
        elif main_pos == "名詞":
            prev_was_de = False
            while j < len(morphemes):
                next_m = morphemes[j]
                next_main = next_m.part_of_speech()[0] if next_m.part_of_speech() else ""
                ns = next_m.surface()
                
                can_attach = next_main in {"助動詞", "形容詞"} or ns in {"じゃ", "では", "で"} or (ns == "は" and prev_was_de)
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
        
        meaning, grammar_note, tags = None, None, []
        
        if main_pos in {"名詞", "動詞", "形容詞", "形状詞", "副詞"}:
            lookup_reading = reading
            if base_form != surface or main_pos in {"動詞", "形容詞"}:
                base_m = list(tokenizer.tokenize(base_form, SplitMode.C))
                if base_m:
                    lookup_reading = jaconv.kata2hira(base_m[0].reading_form())
            
            is_counter = "助数詞" in pos_tuple or (main_pos == "接尾辞" and "名詞的" in pos_tuple)
            details = jmdict.lookup_details(base_form, lookup_reading, is_counter=is_counter)
            meaning = details["meaning"] if details else None
            tags = details["tags"] if details else []
            if meaning and len(meaning) > 30:
                meaning = meaning[:30] + "..."
        
        grammar_note = GRAMMAR_MAP.get(base_form) or GRAMMAR_MAP.get(surface)
        
        # Conjugation analysis
        conjugation_info = None
        if main_pos == "動詞" and compound_surface != base_form:
            type2 = is_verb_type2(pos_tuple)
            conjugation_info = try_deconjugate_verb(compound_surface, base_form, type2, meaning or "")
        elif main_pos == "形状詞" and compound_surface != base_form:
            conjugation_info = _analyze_na_adjective_conjugation(compound_surface)
        elif main_pos == "形容詞" and compound_surface != base_form:
            conjugation_info = _analyze_i_adjective_conjugation(compound_surface)
        elif main_pos == "名詞" and compound_surface != base_form:
            conjugation_info = _analyze_noun_copula(compound_surface)
        
        phrases.append(PhraseToken(
            surface=compound_surface, base=base_form, reading=compound_reading,
            pos=pos_english, meaning=meaning, grammar_note=grammar_note,
            tags=tags, conjugation=conjugation_info,
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
    
    return FullAnalyzeResponse(phrases=phrases, count=len(phrases), text_result="\n".join(text_lines))


def _analyze_na_adjective_conjugation(compound: str) -> ConjugationInfo | None:
    """Analyze na-adjective conjugation patterns."""
    patterns = [
        ("でした", "past (polite)", "was (polite)"),
        ("だった", "past", "was"),
        ("じゃなかった", "negative past", "was not"),
        ("ではなかった", "negative past", "was not"),
        ("じゃない", "negative", "is not"),
        ("ではない", "negative", "is not"),
        ("です", "copula (polite)", "is (polite)"),
        ("だ", "copula", "is"),
    ]
    for suffix, summary, hint in patterns:
        if suffix in compound or compound.endswith(suffix):
            return ConjugationInfo(
                chain=[ConjugationLayer(form="", type="NA_COPULA", english=summary, meaning=hint)],
                summary=summary, translation_hint=hint,
            )
    return None


def _analyze_i_adjective_conjugation(compound: str) -> ConjugationInfo | None:
    """Analyze i-adjective conjugation patterns."""
    patterns = [
        ("くなかった", "negative past", "was not"),
        ("かった", "past", "was"),
        ("くない", "negative", "not"),
        ("くて", "te-form", "and (connecting)"),
        ("ければ", "conditional", "if"),
    ]
    for suffix, summary, hint in patterns:
        if compound.endswith(suffix):
            return ConjugationInfo(
                chain=[ConjugationLayer(form="", type="I_ADJ", english=summary, meaning=hint)],
                summary=summary, translation_hint=hint,
            )
    return None


def _analyze_noun_copula(compound: str) -> ConjugationInfo | None:
    """Analyze noun + copula conjugation patterns."""
    return _analyze_na_adjective_conjugation(compound)  # Same patterns


def deconjugate_word(word: str, dictionary_form: str | None = None, word_type: str = "auto") -> DeconjugateResponse:
    """Deep analysis of a conjugated word."""
    analyzer = JapaneseAnalyzer.get_instance()
    jmdict = analyzer._jmdict
    
    dict_form = dictionary_form
    original_dict_form = dictionary_form
    detected_type = word_type
    
    if not dict_form:
        tokenizer = analyzer._tokenizer
        # Use SplitMode.C to catch suru-verbs and compounds
        morphemes = list(tokenizer.tokenize(word, SplitMode.C))
        if morphemes:
            dict_form = morphemes[0].dictionary_form()
            pos = morphemes[0].part_of_speech()
            main_pos = pos[0] if pos else ""
            
            if main_pos == "動詞":
                detected_type = "verb"
                
                # Check for Ra-nuki potential (食べれる -> 食べる)
                # Sudachi has 食べれる in its dictionary, but JMDict does not
                if dict_form.endswith("れる") and len(dict_form) > 2:
                    potential_base = dict_form[:-2] + "る"
                    base_details = jmdict.lookup_details(potential_base)
                    if base_details and base_details.get("meaning"):
                        # It's a Ra-nuki form, normalize to actual base verb
                        dict_form = potential_base
                        
            elif main_pos == "形容詞" or main_pos == "形状詞":
                # 形状詞 (keijoushi) = Adjectival Noun (Na-adjective)
                detected_type = "adjective"
            
            # Check for suru-verb if it's a noun
            original_dict_form = dict_form
            if detected_type == "auto" and main_pos == "名詞":
                # If we have a noun, check if it's a suru verb candidate
                # We can check JMDict or just optimistically try "term+suru" if it fails
                details = jmdict.lookup_details(dict_form)
                if details and "Suru verb" in details.get("tags", []):
                    # It's a suru verb noun, convert to verb form for conjugation
                    dict_form += "する"
                    detected_type = "verb"
    
    if not dict_form:
        raise ValueError("Could not determine dictionary form")
    
    # Get reading for accurate lookup
    dict_reading = None
    if jmdict.is_loaded:
        base_tokens = list(analyzer._tokenizer.tokenize(original_dict_form, SplitMode.C))
        if base_tokens:
            base_r = jaconv.kata2hira(base_tokens[0].reading_form())
            # Validate reading consistency for verbs/adjectives to avoid homonym errors
            # e.g. "好かれる" -> "suka" vs "好く" -> "yoku" (wrong)
            if morphemes:
                 surface_r = jaconv.kata2hira(morphemes[0].reading_form())
                 if surface_r and base_r:
                     # Check first character consistency (heuristic)
                     # Allow d/j mismatch for da/ja, but s/y is definitely wrong
                     match_start = (surface_r[0] == base_r[0])
                     if not match_start:
                         # Exceptions for irregulars
                         # da -> ja/de/na (d/j/n)
                         if dict_form == "だ" and surface_r[0] in "じでな": match_start = True
                         # iku -> itta (i/i) - ok
                         # kuru -> ko (k/k) - ok
                         # suru -> shi (s/s) - ok
                         
                     if match_start:
                         dict_reading = base_r
                     elif main_pos == "動詞" and "五段" in morphemes[0].part_of_speech()[4]:
                         # Mismatch detected (e.g. Suka vs Yoku).
                         # Try to infer correct base reading from surface reading (Godan only)
                         # Simple mapping of last kana to u-row
                         last = surface_r[-1]
                         stem = surface_r[:-1]
                         
                         vowel_map = {
                             "か": "く", "き": "く", "く": "く", "け": "く", "こ": "く",
                             "が": "ぐ", "ぎ": "ぐ", "ぐ": "ぐ", "げ": "ぐ", "ご": "ぐ",
                             "さ": "す", "し": "す", "す": "す", "せ": "す", "そ": "す",
                             "た": "つ", "ち": "つ", "つ": "つ", "て": "つ", "と": "つ",
                             "な": "ぬ", "に": "ぬ", "ぬ": "ぬ", "ね": "ぬ", "の": "ぬ",
                             "は": "ふ", "ひ": "ふ", "ふ": "ふ", "へ": "ふ", "ほ": "ふ",
                             "ば": "ぶ", "び": "ぶ", "ぶ": "ぶ", "べ": "ぶ", "ぼ": "ぶ",
                             "ま": "む", "み": "む", "む": "む", "め": "む", "も": "む",
                             "ら": "る", "り": "る", "る": "る", "れ": "る", "ろ": "る",
                             # Wa row (for verbs ending in u) - tricky (wa, i, u, e, o -> u)
                             "わ": "う", "い": "う", "う": "う", "え": "う", "お": "う",
                         }
                         if last in vowel_map:
                             # Check if inferred reading starts correctly
                             inferred = stem + vowel_map[last]
                             if inferred[0] == surface_r[0]:
                                 dict_reading = inferred
            else:
                dict_reading = base_r
    
    meaning = jmdict.lookup(original_dict_form, dict_reading)
    layers, alternatives = [], []
    full_breakdown, natural_english = "", ""
    
    if detected_type in {"verb", "auto"}:
        results = deconjugate_verb(word, dict_form, type2=True, max_aux_depth=3)
        verb_is_type2 = True
        if not results:
            results = deconjugate_verb(word, dict_form, type2=False, max_aux_depth=3)
            verb_is_type2 = False
        
        if results:
            best = results[0]
            for aux in best.auxiliaries:
                short_name, aux_meaning = get_auxiliary_info(aux)
                layers.append(ConjugationLayer(form="", type=aux.name, english=short_name, meaning=aux_meaning))
            
            conj_short, conj_meaning = get_conjugation_info(best.conjugation)
            if best.conjugation != Conjugation.DICTIONARY:
                layers.append(ConjugationLayer(form="", type=best.conjugation.name, english=conj_short, meaning=conj_meaning))
            
            parts = [get_auxiliary_info(a)[0] for a in best.auxiliaries]
            if best.conjugation != Conjugation.DICTIONARY:
                parts.append(conj_short)
            full_breakdown = " + ".join(parts) if parts else "dictionary form"
            natural_english = generate_translation_hint(meaning or "", best.auxiliaries, best.conjugation, type2=verb_is_type2)
            
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
            layers.append(ConjugationLayer(form="", type=best.conjugation.name, english=conj_name, meaning=""))
            full_breakdown = conj_name
            natural_english = generate_adjective_hint(meaning or "", best.conjugation)
            detected_type = "adjective"
    
    return DeconjugateResponse(
        word=word, dictionary_form=dict_form,
        word_type=detected_type if detected_type != "auto" else "unknown",
        meaning=meaning, layers=layers, full_breakdown=full_breakdown or "unknown form",
        natural_english=natural_english, alternatives=alternatives if alternatives else None,
    )


def conjugate_word(word: str, word_type: str, requested_forms: list[str] | None = None) -> ConjugateResponse:
    """Generate conjugations from a dictionary form."""
    conjugations: dict[str, list[str]] = {}
    
    if word_type == "verb":
        type2 = False
        if word.endswith("る") and len(word) >= 2:
            try:
                analyzer = JapaneseAnalyzer.get_instance()
                morphemes = list(analyzer._tokenizer.tokenize(word, SplitMode.A))
                if morphemes:
                    type2 = is_verb_type2(morphemes[0].part_of_speech())
            except Exception:
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
                    result = conjugate_auxiliaries(word, auxs, conj, type2) if auxs else conjugate(word, conj, type2)
                    conjugations[form_name] = [r for r in result if len(r) > 1]
                except Exception:
                    conjugations[form_name] = []
    
    elif word_type == "i-adjective":
        if not requested_forms:
            requested_forms = ["negative", "past", "negative_past", "te", "adverbial"]
        
        form_map = {
            "negative": AdjConjugation.NEGATIVE, "past": AdjConjugation.PAST,
            "negative_past": AdjConjugation.NEGATIVE_PAST, "te": AdjConjugation.CONJUNCTIVE_TE,
            "adverbial": AdjConjugation.ADVERBIAL, "conditional": AdjConjugation.CONDITIONAL,
        }
        
        for form_name in requested_forms:
            form_key = form_name.lower().replace("-", "_").replace(" ", "_")
            if form_key in form_map:
                try:
                    conjugations[form_name] = conjugate_adjective(word, form_map[form_key], is_i_adjective=True)
                except Exception:
                    conjugations[form_name] = []
    
    elif word_type == "na-adjective":
        if not requested_forms:
            requested_forms = ["prenominal", "negative", "past", "te", "adverbial"]
        
        form_map = {
            "prenominal": AdjConjugation.PRENOMINAL, "negative": AdjConjugation.NEGATIVE,
            "past": AdjConjugation.PAST, "te": AdjConjugation.CONJUNCTIVE_TE,
            "adverbial": AdjConjugation.ADVERBIAL,
        }
        
        for form_name in requested_forms:
            form_key = form_name.lower().replace("-", "_").replace(" ", "_")
            if form_key in form_map:
                try:
                    conjugations[form_name] = conjugate_adjective(word, form_map[form_key], is_i_adjective=False)
                except Exception:
                    conjugations[form_name] = []
    
    return ConjugateResponse(word=word, word_type=word_type, conjugations=conjugations)


def tokenize_raw(text: str) -> dict:
    """Raw Sudachi tokenization output for debugging."""
    analyzer = JapaneseAnalyzer.get_instance()
    
    tokens, lines = [], []
    for m in analyzer._tokenizer.tokenize(text, SplitMode.C):
        pos_list = list(m.part_of_speech())
        tokens.append({
            "surface": m.surface(), "dictionary_form": m.dictionary_form(),
            "reading": m.reading_form(), "normalized_form": m.normalized_form(),
            "pos": pos_list, "is_oov": m.is_oov(),
        })
        pos_short = "-".join([p for p in pos_list[:2] if p != "*"])
        lines.append(f"{m.surface()} -> {m.dictionary_form()} [{pos_short}] {m.reading_form()}")
    
    return {"tokens": tokens, "count": len(tokens), "result": "\n".join(lines)}

