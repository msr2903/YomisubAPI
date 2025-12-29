"""Helper functions for conjugation service."""

from lemminflect import getInflection

from services.verb import Conjugation, Auxiliary, deconjugate_verb
from models import ConjugationLayer, ConjugationInfo

from .data import AUXILIARY_DESCRIPTIONS, CONJUGATION_DESCRIPTIONS


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
