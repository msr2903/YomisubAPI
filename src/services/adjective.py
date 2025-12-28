"""Japanese adjective conjugation and deconjugation.

Supports both i-adjectives (形容詞) and na-adjectives (形容動詞).

Based on Kamiya's conjugation patterns with extensions for
complex forms like 食べられなかった (potential + negative + past).
"""

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Literal


class AdjConjugation(StrEnum):
    """Adjective conjugation forms."""
    
    PRESENT = auto()          # 高い / 静かだ
    PRENOMINAL = auto()       # 高い / 静かな (before nouns)
    NEGATIVE = auto()         # 高くない / 静かではない
    PAST = auto()             # 高かった / 静かだった
    NEGATIVE_PAST = auto()    # 高くなかった / 静かではなかった
    CONJUNCTIVE_TE = auto()   # 高くて / 静かで
    ADVERBIAL = auto()        # 高く / 静かに
    CONDITIONAL = auto()      # 高ければ / 静かなら
    TARA_CONDITIONAL = auto() # 高かったら / 静かだったら
    TARI = auto()             # 高かったり / 静かだったり
    NOUN = auto()             # 高さ / 静かさ
    STEM_SOU = auto()         # 高そう / 静かそう (looks ~)
    STEM_NEGATIVE_SOU = auto() # 高くなさそう / 静かじゃなさそう


@dataclass(frozen=True, slots=True)
class AdjDeconjugated:
    """Result of adjective deconjugation."""
    
    conjugation: AdjConjugation
    result: list[str]


def _conjugate_i_adjective(stem: str, conjugation: AdjConjugation, add_sa: bool) -> list[str]:
    """Conjugate an i-adjective given its stem.
    
    Args:
        stem: The adjective stem (e.g., 高 from 高い)
        conjugation: The target conjugation form
        add_sa: Whether to add さ before そう (for いい and ない forms)
    
    Returns:
        List of possible conjugated forms
    """
    match conjugation:
        case AdjConjugation.PRESENT:
            return [stem + "い"]
        case AdjConjugation.PRENOMINAL:
            return [stem + "い"]
        case AdjConjugation.NEGATIVE:
            return [stem + "くない"]
        case AdjConjugation.PAST:
            return [stem + "かった"]
        case AdjConjugation.NEGATIVE_PAST:
            return [stem + "くなかった"]
        case AdjConjugation.CONJUNCTIVE_TE:
            return [stem + "く", stem + "くて"]
        case AdjConjugation.ADVERBIAL:
            return [stem + "く"]
        case AdjConjugation.CONDITIONAL:
            return [stem + "ければ"]
        case AdjConjugation.TARA_CONDITIONAL:
            return [stem + "かったら"]
        case AdjConjugation.TARI:
            return [stem + "かったり"]
        case AdjConjugation.NOUN:
            return [stem + "さ"]
        case AdjConjugation.STEM_SOU:
            return [stem + "さそう"] if add_sa else [stem + "そう"]
        case AdjConjugation.STEM_NEGATIVE_SOU:
            # Negative stem + さそう
            return [stem + "くなさそう"]
        case _:
            raise ValueError(f"Unknown conjugation: {conjugation}")


def _conjugate_na_adjective(base: str, conjugation: AdjConjugation) -> list[str]:
    """Conjugate a na-adjective.
    
    Args:
        base: The adjective base (e.g., 静か)
        conjugation: The target conjugation form
    
    Returns:
        List of possible conjugated forms
    """
    match conjugation:
        case AdjConjugation.PRENOMINAL:
            return [base + "な"]
        case AdjConjugation.PRESENT:
            return [base + suffix for suffix in ["だ", "です", "でございます"]]
        case AdjConjugation.NEGATIVE:
            return [base + suffix for suffix in ["ではない", "でない", "じゃない", "ではありません"]]
        case AdjConjugation.PAST:
            return [base + suffix for suffix in ["だった", "でした"]]
        case AdjConjugation.NEGATIVE_PAST:
            return [base + suffix for suffix in ["ではなかった", "でなかった", "じゃなかった", "ではありませんでした"]]
        case AdjConjugation.CONJUNCTIVE_TE:
            return [base + "で"]
        case AdjConjugation.ADVERBIAL:
            return [base + "に"]
        case AdjConjugation.CONDITIONAL:
            return [base + suffix for suffix in ["なら", "ならば"]]
        case AdjConjugation.TARA_CONDITIONAL:
            return [base + "だったら"]
        case AdjConjugation.TARI:
            return [base + suffix for suffix in ["だったり", "でしたり"]]
        case AdjConjugation.NOUN:
            return [base + "さ"]
        case AdjConjugation.STEM_SOU:
            return [base + "そう"]
        case AdjConjugation.STEM_NEGATIVE_SOU:
            return [base + "じゃなさそう"]
        case _:
            raise ValueError(f"Unknown conjugation: {conjugation}")


def conjugate_adjective(
    adjective: str,
    conjugation: AdjConjugation,
    is_i_adjective: bool = True,
) -> list[str]:
    """Conjugate a Japanese adjective.
    
    Args:
        adjective: Dictionary form of the adjective (e.g., 高い, 静か)
        conjugation: Target conjugation form
        is_i_adjective: True for i-adjectives, False for na-adjectives
    
    Returns:
        List of possible conjugated forms
    
    Examples:
        >>> conjugate_adjective("高い", AdjConjugation.NEGATIVE, True)
        ['高くない']
        >>> conjugate_adjective("静か", AdjConjugation.PRENOMINAL, False)
        ['静かな']
    """
    if is_i_adjective:
        # Handle irregular いい/良い/よい
        stem: str
        add_sa = False
        
        if adjective in ("いい", "良い", "よい"):
            stem = "良" if adjective.startswith("良") else "よ"
            add_sa = True
        elif adjective.endswith("ない"):
            # Adjectives ending in ない (like つまらない) need さ before そう
            stem = adjective[:-1]
            add_sa = True
        else:
            stem = adjective[:-1]  # Remove い
        
        return _conjugate_i_adjective(stem, conjugation, add_sa)
    
    # na-adjective
    return _conjugate_na_adjective(adjective, conjugation)


def deconjugate_adjective(
    conjugated: str,
    dictionary_form: str,
    is_i_adjective: bool = True,
) -> list[AdjDeconjugated]:
    """Identify the conjugation form(s) of a conjugated adjective.
    
    Args:
        conjugated: The conjugated form to analyze
        dictionary_form: The dictionary form of the adjective
        is_i_adjective: True for i-adjectives, False for na-adjectives
    
    Returns:
        List of matching AdjDeconjugated results
    
    Examples:
        >>> results = deconjugate_adjective("高くなかった", "高い", True)
        >>> results[0].conjugation
        <AdjConjugation.NEGATIVE_PAST: 'negative_past'>
    """
    hits: list[AdjDeconjugated] = []
    
    for conj in AdjConjugation:
        result = conjugate_adjective(dictionary_form, conj, is_i_adjective)
        if conjugated in result:
            hits.append(AdjDeconjugated(conjugation=conj, result=result))
    
    return hits


# Additional helper functions for integration with analyzer

def get_adjective_stem(adjective: str, is_i_adjective: bool = True) -> str:
    """Get the stem of an adjective.
    
    Args:
        adjective: Dictionary form of the adjective
        is_i_adjective: True for i-adjectives, False for na-adjectives
    
    Returns:
        The adjective stem
    """
    if is_i_adjective:
        if adjective in ("いい", "良い", "よい"):
            return "良" if adjective.startswith("良") else "よ"
        return adjective[:-1]
    return adjective


def identify_adjective_type(adjective: str) -> Literal["i", "na", "unknown"]:
    """Attempt to identify adjective type from dictionary form.
    
    Note: This is a heuristic and may not always be accurate.
    Use JMDict for authoritative classification.
    
    Args:
        adjective: The adjective to classify
    
    Returns:
        "i" for i-adjectives, "na" for na-adjectives, "unknown" if unclear
    """
    # Common exceptions (na-adjectives ending in い)
    na_adj_ending_i = frozenset({
        "きれい", "綺麗", "嫌い", "きらい", "有名", "ゆうめい"
    })
    
    if adjective in na_adj_ending_i:
        return "na"
    
    if adjective.endswith("い"):
        return "i"
    
    # Common na-adjective endings
    if adjective.endswith(("的", "な")):
        return "na"
    
    return "unknown"
