"""Helper functions for conjugation service."""

from lemminflect import getInflection

from services.verb import Conjugation, Auxiliary, deconjugate_verb
from services.adjective import AdjConjugation
from models import ConjugationLayer, ConjugationInfo

from .data import AUXILIARY_DESCRIPTIONS, CONJUGATION_DESCRIPTIONS
from .phrases import match_phrase_suffix
from services.adjective import deconjugate_adjective, identify_adjective_type


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
    type2: bool = True,
) -> str:
    """Generate a natural English translation hint.
    
    Args:
        base_meaning: The dictionary meaning of the verb
        auxiliaries: Tuple of auxiliaries applied to the verb
        conjugation: Final conjugation form
        type2: True for ichidan verbs, False for godan. Affects RERU_RARERU interpretation:
               - Godan (type2=False): RERU_RARERU is passive only ("is done")
               - Ichidan (type2=True): RERU_RARERU is ambiguous ("can/is done")
    """
    if not base_meaning:
        return ""
    
    first_meaning = base_meaning.split(";")[0].split(",")[0].strip()
    if first_meaning.startswith("to "):
        first_meaning = first_meaning[3:]
    
    hint = first_meaning
    has_potential = False  # Track if potential was applied
    
    for aux in auxiliaries:
        match aux:
            case Auxiliary.POTENTIAL:
                hint = f"can {hint}"
                has_potential = True
            case Auxiliary.RERU_RARERU:
                # For godan verbs: RERU_RARERU is passive only (potential uses え-stem + る)
                # For ichidan verbs: RERU_RARERU is ambiguous (can be passive or potential)
                if type2:
                    # Ichidan: ambiguous, default to potential interpretation
                    hint = f"can {hint}"
                    has_potential = True
                else:
                    # Godan: passive only
                    hint = f"is {hint}"
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
            case Auxiliary.NASAI:
                hint = f"please {hint}"
            case Auxiliary.MASU:
                pass
            case _:
                pass
    
    match conjugation:
        case Conjugation.NEGATIVE | Conjugation.ZU | Conjugation.NU:
             if hint.startswith("can "):
                 hint = hint.replace("can ", "cannot ")
             else:
                 hint = f"not {hint}"
        case Conjugation.TA:
            if hint.endswith("ing"):
                pass  # Keep -ing form for processing
            elif "can " in hint and "not" in hint:
                # Potential + negative + past: "couldn't eat" (not "didn't eat")
                verb = hint.replace("not ", "").replace("can ", "")
                hint = f"couldn't {verb}"
            elif "not" in hint:
                # Just negative + past: "didn't eat"
                verb = hint.replace("not ", "").replace("can ", "")
                hint = f"didn't {verb}"
            elif "can " in hint:
                # Potential + past: "could eat"
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


def generate_adjective_hint(
    base_meaning: str,
    conjugation: AdjConjugation,
) -> str:
    """Generate a natural English translation hint for adjectives."""
    if not base_meaning:
        return ""
    
    # Clean up meaning (take first one, remove "to ")
    hint = base_meaning.split(";")[0].split(",")[0].strip()
    if hint.startswith("to "):
        hint = hint[3:]
    
    match conjugation:
        case AdjConjugation.PRESENT:
            hint = f"is {hint}"
        case AdjConjugation.PRENOMINAL:
            pass # "high" (attributive)
        case AdjConjugation.NEGATIVE:
            hint = f"is not {hint}"
        case AdjConjugation.PAST:
            hint = f"was {hint}"
        case AdjConjugation.NEGATIVE_PAST:
            hint = f"was not {hint}"
        case AdjConjugation.CONJUNCTIVE_TE:
            hint = f"is {hint} and..."
        case AdjConjugation.ADVERBIAL:
            hint = f"{hint}ly" # This is rough, e.g. "quietly", but "high" -> "highly"?
        case AdjConjugation.CONDITIONAL:
            hint = f"if {hint}"
        case AdjConjugation.TARA_CONDITIONAL:
            hint = f"if was {hint}"
        case AdjConjugation.TARI:
            hint = f"was {hint} and..."
        case AdjConjugation.NOUN:
            hint = f"{hint}ness" # rough
        case AdjConjugation.STEM_SOU:
            hint = f"looks {hint}"
        case AdjConjugation.STEM_NEGATIVE_SOU:
            hint = f"doesn't look {hint}"
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
    
    # Check compound phrases first (e.g. nakerebanarimasen -> must)
    phrase_match = match_phrase_suffix(surface)
    if phrase_match:
        suffix, phrase_meaning, stem = phrase_match
        # Create a phrase conjugation info
        main_meaning = meaning.split(";")[0].split(",")[0].strip()
        if main_meaning.startswith("to "): main_meaning = main_meaning[3:]
        
        # Format: "must eat", "want someone to eat"
        # phrase_meaning: "must; have to"
        clean_phrase = phrase_meaning.split(";")[0].strip()
        
        # Heuristic translation hint construction
        if "{verb}" in clean_phrase:
            hint = clean_phrase.format(verb=main_meaning)
        else:
            hint = f"{clean_phrase} {main_meaning}"
            
        info = ConjugationInfo(
            chain=[ConjugationLayer(
                form="", type="PHRASE", english=clean_phrase, meaning=phrase_meaning
            )],
            summary=clean_phrase,
            translation_hint=hint,
        )
        return info
    
    try:
        results = deconjugate_verb(surface, base_form, type2=type2, max_aux_depth=2)
        if results:
            r = results[0]
            info = build_conjugation_info(r.auxiliaries, r.conjugation, meaning)
            info.translation_hint = generate_translation_hint(meaning, r.auxiliaries, r.conjugation, type2)
            return info
    except Exception:
        pass
    
    return None


def try_deconjugate_adjective(
    surface: str,
    base_form: str,
    meaning: str = "",
) -> ConjugationInfo | None:
    """Try to deconjugate an adjective."""
    if surface == base_form:
        return None
        
    try:
        # Determine strict i-adj vs na-adj logic?
        # We can try both or use identify_adjective_type.
        # analysis.py knows the POS (形容詞 vs 形状詞), but here we might just have strings.
        # But wait, try_deconjugate_adjective is called from analysis.py which knows POS.
        # We should probably pass is_i_adjective.
        # But if we don't, we can guess.
        
        # Heuristic guess
        is_i = identify_adjective_type(base_form) == "i"
        
        results = deconjugate_adjective(surface, base_form, is_i_adjective=is_i)
        if not results and not is_i:
             # Try i-adj just in case (some na-adjectives act like i-adj like kirei?)
             # No, kirei is na-adj ending in i.
             pass
             
        if results:
            best = results[0]
            conj_layer = ConjugationLayer(
                form="",
                type=best.conjugation.name,
                english=best.conjugation.name.replace("_", " ").lower(),
                meaning=""
            )
            hint = generate_adjective_hint(meaning, best.conjugation)
            return ConjugationInfo(
                chain=[conj_layer],
                summary=best.conjugation.name.replace("_", " ").lower(),
                translation_hint=hint
            )
            
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
