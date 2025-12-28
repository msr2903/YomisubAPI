"""Japanese verb conjugation and deconjugation.

Supports:
- Type I (godan/五段) verbs: 書く, 飲む, 行く, etc.
- Type II (ichidan/一段) verbs: 食べる, 見る, etc.
- Irregular verbs: する, くる/来る, だ, です
- Auxiliary constructions: potential, passive, causative, etc.

Based on Kamiya's "Japanese Verbs & Essentials of Grammar" with
extensions for complex multi-auxiliary chains like:
- 食べられなかった (eat + potential + negative + past)
- 言われてみれば (say + passive + te + miru + conditional)
"""

from dataclasses import dataclass
from enum import StrEnum, auto


class Conjugation(StrEnum):
    """Base verb conjugation forms (活用形)."""
    
    NEGATIVE = auto()      # 未然形 + ない
    CONJUNCTIVE = auto()   # 連用形 (masu stem)
    DICTIONARY = auto()    # 終止形/辞書形
    CONDITIONAL = auto()   # 仮定形
    IMPERATIVE = auto()    # 命令形
    VOLITIONAL = auto()    # 意志形
    TE = auto()            # て形
    TA = auto()            # た形 (past)
    TARA = auto()          # たら形 (conditional)
    TARI = auto()          # たり形 (listing)
    ZU = auto()            # ず (classical negative)
    NU = auto()            # ぬ (classical negative attributive)


class Auxiliary(StrEnum):
    """Auxiliary verb constructions (助動詞)."""
    
    # Grammatical auxiliaries
    POTENTIAL = auto()           # れる/える - can do
    MASU = auto()                # ます - polite
    NAI = auto()                 # ない - negative
    TAI = auto()                 # たい - want to
    TAGARU = auto()              # たがる - seems to want
    HOSHII = auto()              # ほしい - want (someone to)
    RASHII = auto()              # らしい - apparently
    SOUDA_HEARSAY = auto()       # そうだ - I heard
    SOUDA_CONJECTURE = auto()    # そうだ - looks like
    
    # Causative/Passive
    SERU_SASERU = auto()         # せる/させる - causative
    SHORTENED_CAUSATIVE = auto() # す - shortened causative
    RERU_RARERU = auto()         # れる/られる - passive/potential
    CAUSATIVE_PASSIVE = auto()   # させられる
    SHORTENED_CAUSATIVE_PASSIVE = auto()  # される
    
    # Giving/Receiving (授受動詞)
    AGERU = auto()               # あげる - give (to equal/inferior)
    SASHIAGERU = auto()          # 差し上げる - give (humble)
    YARU = auto()                # やる - give (casual)
    MORAU = auto()               # もらう - receive
    ITADAKU = auto()             # いただく - receive (humble)
    KURERU = auto()              # くれる - give (to me)
    KUDASARU = auto()            # くださる - give (to me, humble)
    
    # Aspect/Direction
    TE_IRU = auto()              # ている - continuous/resultative
    TE_ARU = auto()              # てある - resultative
    MIRU = auto()                # てみる - try doing
    IKU = auto()                 # ていく - going
    KURU = auto()                # てくる - coming
    OKU = auto()                 # ておく - prepare
    SHIMAU = auto()              # てしまう - complete/regret
    TE_ORU = auto()              # ておる - humble/dialectal continuous
    
    # Degree/Manner
    SUGIRU = auto()              # すぎる - too much
    YASUI = auto()               # やすい - easy to
    NIKUI = auto()               # にくい - hard to
    
    # Aspect (start/end/continue)
    HAJIMERU = auto()            # 始める - start doing
    OWARU = auto()               # 終わる - finish doing
    TSUZUKERU = auto()           # 続ける - continue doing
    DASU = auto()                # 出す - burst into (action)
    
    # Appearance
    GARU = auto()                # がる - seems (3rd person wanting)
    SOU_APPEARANCE = auto()      # そう - looks like (appearance)


# Hiragana vowel lookup table for verb conjugation
_HIRAGANA_TABLE = {
    # Base -> [あ段, い段, う段, え段, お段]
    "う": ["わ", "い", "う", "え", "お"],
    "く": ["か", "き", "く", "け", "こ"],
    "ぐ": ["が", "ぎ", "ぐ", "げ", "ご"],
    "す": ["さ", "し", "す", "せ", "そ"],
    "ず": ["ざ", "じ", "ず", "ぜ", "ぞ"],
    "つ": ["た", "ち", "つ", "て", "と"],
    "づ": ["だ", "ぢ", "づ", "で", "ど"],
    "ぬ": ["な", "に", "ぬ", "ね", "の"],
    "ふ": ["は", "ひ", "ふ", "へ", "ほ"],
    "ぶ": ["ば", "び", "ぶ", "べ", "ぼ"],
    "ぷ": ["ぱ", "ぴ", "ぷ", "ぺ", "ぽ"],
    "む": ["ま", "み", "む", "め", "も"],
    "る": ["ら", "り", "る", "れ", "ろ"],
}


def _lookup_hiragana(base: str, index: int) -> str:
    """Look up hiragana in the vowel row.
    
    Args:
        base: Base hiragana character
        index: 0=あ段, 1=い段, 2=う段, 3=え段, 4=お段
    
    Returns:
        The corresponding hiragana character
    """
    if base not in _HIRAGANA_TABLE:
        raise ValueError(f"Unknown hiragana base: {base}")
    return _HIRAGANA_TABLE[base][index]


# Te/Ta form sound changes (音便)
_TE_TA_FORMS = {
    # final char -> [te, ta, tara, tari]
    "く": ["いて", "いた", "いたら", "いたり"],
    "ぐ": ["いで", "いだ", "いだら", "いだり"],  # rendaku
    "す": ["して", "した", "したら", "したり"],
    "ぬ": ["んで", "んだ", "んだら", "んだり"],  # nasalization
    "ぶ": ["んで", "んだ", "んだら", "んだり"],
    "む": ["んで", "んだ", "んだら", "んだり"],
    "つ": ["って", "った", "ったら", "ったり"],  # gemination
    "る": ["って", "った", "ったら", "ったり"],
    "う": ["って", "った", "ったら", "ったり"],
}


# Special case verbs
_SPECIAL_CASES: dict[str, dict[Conjugation, str]] = {
    "ある": {Conjugation.NEGATIVE: ""},  # ない only
    "ござる": {Conjugation.CONJUNCTIVE: "ござい"},
    "いらっしゃる": {
        Conjugation.CONJUNCTIVE: "いらっしゃい",
        Conjugation.CONDITIONAL: "いらっしゃい",
        Conjugation.IMPERATIVE: "いらっしゃい",
    },
}


# Conjugation to index mapping for godan verbs
_CONJ_TO_INDEX = {
    Conjugation.NEGATIVE: 0,    # あ段
    Conjugation.ZU: 0,
    Conjugation.NU: 0,
    Conjugation.CONJUNCTIVE: 1,  # い段
    Conjugation.DICTIONARY: 2,   # う段
    Conjugation.CONDITIONAL: 3,  # え段
    Conjugation.VOLITIONAL: 4,   # お段
}


def _conjugate_type1(verb: str, conj: Conjugation) -> list[str]:
    """Conjugate a Type I (godan) verb.
    
    Args:
        verb: Dictionary form of the verb
        conj: Target conjugation
    
    Returns:
        List of conjugated forms
    """
    # Handle special verbs first
    if verb == "する":
        return _conjugate_suru(conj)
    if verb in ("くる", "来る"):
        return _conjugate_kuru(verb, conj)
    if verb == "だ":
        return _conjugate_da(conj)
    if verb == "です":
        return _conjugate_desu(conj)
    if verb.endswith("くださる"):
        if conj == Conjugation.DICTIONARY:
            return [verb]
        if conj == Conjugation.CONJUNCTIVE:
            return [verb[:-2] + "さい"]
        raise ValueError(f"Unknown conjugation for -kudasaru: {conj}")
    
    # Check special cases
    if verb in _SPECIAL_CASES and conj in _SPECIAL_CASES[verb]:
        return [_SPECIAL_CASES[verb][conj]]
    
    head = verb[:-1]
    tail = verb[-1]
    
    # Handle non-te/ta conjugations
    if conj in _CONJ_TO_INDEX:
        idx = _CONJ_TO_INDEX[conj]
        
        # Special case for う ending with negative (わ not あ)
        if tail == "う" and idx == 0:
            return [head + "わ"]
        
        return [head + _lookup_hiragana(tail, idx)]
    
    # Imperative uses え段
    if conj == Conjugation.IMPERATIVE:
        return [head + _lookup_hiragana(tail, 3)]
    
    # Te/Ta forms
    te_ta_idx = {
        Conjugation.TE: 0,
        Conjugation.TA: 1,
        Conjugation.TARA: 2,
        Conjugation.TARI: 3,
    }.get(conj)
    
    if te_ta_idx is not None:
        # 行く/いく uses special form (促音便 instead of イ音便)
        lookup_key = "つ" if verb in ("行く", "いく") else tail
        if lookup_key not in _TE_TA_FORMS:
            raise ValueError(f"Unknown verb ending for te/ta forms: {tail}")
        return [head + _TE_TA_FORMS[lookup_key][te_ta_idx]]
    
    raise ValueError(f"Unhandled conjugation: {conj}")


def _conjugate_type2(verb: str, conj: Conjugation) -> list[str]:
    """Conjugate a Type II (ichidan) verb.
    
    Args:
        verb: Dictionary form of the verb
        conj: Target conjugation
    
    Returns:
        List of conjugated forms
    """
    # Check for special verbs
    if verb == "する":
        return _conjugate_suru(conj)
    if verb in ("くる", "来る"):
        return _conjugate_kuru(verb, conj)
    if verb == "だ":
        return _conjugate_da(conj)
    if verb == "です":
        return _conjugate_desu(conj)
    
    head = verb[:-1]  # Remove る
    
    match conj:
        case Conjugation.NEGATIVE | Conjugation.ZU | Conjugation.NU:
            return [head]
        case Conjugation.CONJUNCTIVE:
            return [head]
        case Conjugation.DICTIONARY:
            return [verb]
        case Conjugation.CONDITIONAL:
            return [head + "れ"]
        case Conjugation.IMPERATIVE:
            return [head + "ろ", head + "よ"]
        case Conjugation.VOLITIONAL:
            return [head + "よう"]
        case Conjugation.TE:
            return [head + "て"]
        case Conjugation.TA:
            return [head + "た"]
        case Conjugation.TARA:
            return [head + "たら"]
        case Conjugation.TARI:
            return [head + "たり"]
        case _:
            raise ValueError(f"Unhandled conjugation: {conj}")


def _conjugate_kuru(verb: str, conj: Conjugation) -> list[str]:
    """Conjugate くる/来る (to come)."""
    is_kanji = verb.startswith("来")
    prefix = "来" if is_kanji else ""
    
    match conj:
        case Conjugation.NEGATIVE | Conjugation.ZU | Conjugation.NU:
            return [prefix + "こ"]
        case Conjugation.CONJUNCTIVE:
            return [prefix + "き"]
        case Conjugation.DICTIONARY:
            return [prefix + "くる"]
        case Conjugation.CONDITIONAL:
            return [prefix + "くれ"]
        case Conjugation.IMPERATIVE:
            return [prefix + "こい"]
        case Conjugation.VOLITIONAL:
            return [prefix + "こよう"]
        case Conjugation.TE:
            return [prefix + "きて"]
        case Conjugation.TA:
            return [prefix + "きた"]
        case Conjugation.TARA:
            return [prefix + "きたら"]
        case Conjugation.TARI:
            return [prefix + "きたり"]
        case _:
            raise ValueError(f"Unhandled conjugation for kuru: {conj}")


def _conjugate_suru(conj: Conjugation) -> list[str]:
    """Conjugate する (to do)."""
    match conj:
        case Conjugation.NEGATIVE:
            return ["し"]
        case Conjugation.CONJUNCTIVE:
            return ["し"]
        case Conjugation.DICTIONARY:
            return ["する"]
        case Conjugation.CONDITIONAL:
            return ["すれ"]
        case Conjugation.IMPERATIVE:
            return ["しろ", "せよ"]
        case Conjugation.VOLITIONAL:
            return ["しよう"]
        case Conjugation.TE:
            return ["して"]
        case Conjugation.TA:
            return ["した"]
        case Conjugation.TARA:
            return ["したら"]
        case Conjugation.TARI:
            return ["したり"]
        case Conjugation.ZU:
            return ["せず"]
        case Conjugation.NU:
            return ["せぬ"]
        case _:
            raise ValueError(f"Unhandled conjugation for suru: {conj}")


def _conjugate_da(conj: Conjugation) -> list[str]:
    """Conjugate だ (copula, plain)."""
    match conj:
        case Conjugation.NEGATIVE:
            return ["でない", "ではない", "じゃない"]
        case Conjugation.DICTIONARY:
            return ["だ"]
        case Conjugation.CONDITIONAL:
            return ["なら"]
        case Conjugation.TE:
            return ["で"]
        case Conjugation.TA:
            return ["だった"]
        case Conjugation.TARA:
            return ["だったら"]
        case Conjugation.TARI:
            return ["だったり"]
        case _:
            raise ValueError(f"Unhandled conjugation for da: {conj}")


def _conjugate_desu(conj: Conjugation) -> list[str]:
    """Conjugate です (copula, polite)."""
    match conj:
        case Conjugation.NEGATIVE:
            return ["でありません", "ではありません"]
        case Conjugation.DICTIONARY:
            return ["です"]
        case Conjugation.TE:
            return ["でして"]
        case Conjugation.TA:
            return ["でした"]
        case Conjugation.TARA:
            return ["でしたら"]
        case Conjugation.TARI:
            return ["でしたり"]
        case _:
            raise ValueError(f"Unhandled conjugation for desu: {conj}")


def _conjugate_strict(verb: str, conj: Conjugation, type2: bool = False) -> list[str]:
    """Conjugate without adding suffixes."""
    if verb[-1] == "る" and type2:
        return _conjugate_type2(verb, conj)
    return _conjugate_type1(verb, conj)


def conjugate(verb: str, conj: Conjugation, type2: bool = False) -> list[str]:
    """Conjugate a verb with complete suffixes where applicable.
    
    This is the main conjugation function that adds appropriate suffixes
    (e.g., ない to negative stem, ます to conjunctive, ば to conditional).
    
    Args:
        verb: Dictionary form of the verb
        conj: Target conjugation
        type2: True for ichidan verbs, False for godan
    
    Returns:
        List of conjugated forms
    
    Examples:
        >>> conjugate("食べる", Conjugation.NEGATIVE, type2=True)
        ['食べ', '食べない']
        >>> conjugate("書く", Conjugation.TE, type2=False)
        ['書いて']
    """
    result = _conjugate_strict(verb, conj, type2)
    
    # Add appropriate suffixes
    if conj in (Conjugation.NEGATIVE, Conjugation.ZU, Conjugation.NU) and verb not in ("だ", "です"):
        if conj == Conjugation.NEGATIVE:
            result.append(result[0] + "ない")
        elif conj == Conjugation.ZU:
            result.append(result[0] + "ず")
        elif conj == Conjugation.NU:
            result.append(result[0] + "ぬ")
    elif conj == Conjugation.CONJUNCTIVE:
        result.append(result[0] + "ます")
    elif conj == Conjugation.CONDITIONAL:
        result.append(result[0] + "ば")
    elif conj == Conjugation.VOLITIONAL:
        result.append(result[0] + "う")
    
    return result


def _conjugate_auxiliary(
    verb: str, 
    aux: Auxiliary,
    conj: Conjugation,
    type2: bool = False,
) -> list[str]:
    """Conjugate a verb with an auxiliary.
    
    Args:
        verb: Dictionary form of the verb
        aux: Auxiliary to apply
        conj: Final conjugation form
        type2: True for ichidan verbs
    
    Returns:
        List of conjugated forms
    """
    match aux:
        case Auxiliary.POTENTIAL:
            # Type I: 書く -> 書ける, Type II: 食べる -> 食べられる/食べれる
            if type2:
                new_verb = _conjugate_type2(verb, Conjugation.CONDITIONAL)[0] + "る"
            else:
                new_verb = _conjugate_type1(verb, Conjugation.CONDITIONAL)[0] + "る"
            return conjugate(new_verb, conj, type2=True)
        
        case Auxiliary.MASU:
            base = conjugate(verb, Conjugation.CONJUNCTIVE, type2)[0]
            match conj:
                case Conjugation.NEGATIVE:
                    return [base + "ません", base + "ませんでした"]
                case Conjugation.DICTIONARY:
                    return [base + "ます"]
                case Conjugation.CONDITIONAL:
                    return [base + "ますれば"]
                case Conjugation.IMPERATIVE:
                    return [base + "ませ", base + "まし"]
                case Conjugation.VOLITIONAL:
                    return [base + "ましょう"]
                case Conjugation.TE:
                    return [base + "まして"]
                case Conjugation.TA:
                    return [base + "ました"]
                case Conjugation.TARA:
                    return [base + "ましたら"]
                case _:
                    raise ValueError(f"Unhandled conjugation for masu: {conj}")
        
        case Auxiliary.NAI:
            base = conjugate(verb, Conjugation.NEGATIVE, type2)[0]
            match conj:
                case Conjugation.NEGATIVE:
                    return [base + "なくはない"]
                case Conjugation.CONJUNCTIVE:
                    return [base + "なく"]
                case Conjugation.DICTIONARY:
                    return [base + "ない"]
                case Conjugation.CONDITIONAL:
                    return [base + "なければ"]
                case Conjugation.TE:
                    return [base + "なくて", base + "ないで"]
                case Conjugation.TA:
                    return [base + "なかった"]
                case Conjugation.TARA:
                    return [base + "なかったら"]
                case _:
                    raise ValueError(f"Unhandled conjugation for nai: {conj}")
        
        case Auxiliary.TAI:
            base = conjugate(verb, Conjugation.CONJUNCTIVE, type2)[0]
            match conj:
                case Conjugation.NEGATIVE:
                    return [base + "たくない"]
                case Conjugation.CONJUNCTIVE:
                    return [base + "たく"]
                case Conjugation.DICTIONARY:
                    return [base + "たい"]
                case Conjugation.CONDITIONAL:
                    return [base + "たければ"]
                case Conjugation.TE:
                    return [base + "たくて"]
                case Conjugation.TA:
                    return [base + "たかった"]
                case Conjugation.TARA:
                    return [base + "たかったら"]
                case _:
                    raise ValueError(f"Unhandled conjugation for tai: {conj}")
        
        case Auxiliary.TAGARU:
            if conj in (Conjugation.CONDITIONAL, Conjugation.IMPERATIVE, 
                       Conjugation.VOLITIONAL, Conjugation.TARI):
                raise ValueError(f"Unhandled conjugation for tagaru: {conj}")
            bases = conjugate(verb, Conjugation.CONJUNCTIVE, type2)
            tagaru_conj = conjugate("たがる", conj, type2=False)
            return [bases[0] + suffix for suffix in tagaru_conj]
        
        case Auxiliary.HOSHII:
            base = conjugate(verb, Conjugation.TE, type2)[0]
            match conj:
                case Conjugation.NEGATIVE:
                    return [base + "ほしくない"]
                case Conjugation.CONJUNCTIVE:
                    return [base + "ほしく"]
                case Conjugation.DICTIONARY:
                    return [base + "ほしい"]
                case Conjugation.CONDITIONAL:
                    return [base + "ほしければ"]
                case Conjugation.TE:
                    return [base + "ほしくて"]
                case Conjugation.TA:
                    return [base + "ほしかった"]
                case Conjugation.TARA:
                    return [base + "ほしかったら"]
                case _:
                    raise ValueError(f"Unhandled conjugation for hoshii: {conj}")
        
        case Auxiliary.RASHII:
            base1 = conjugate(verb, Conjugation.TA, type2)[0]
            base2 = verb
            bases = [base1, base2]
            match conj:
                case Conjugation.NEGATIVE:
                    neg = _conjugate_auxiliary(verb, Auxiliary.NAI, Conjugation.DICTIONARY)[0]
                    return [neg + "らしい"]
                case Conjugation.CONJUNCTIVE:
                    return [b + "らしく" for b in bases]
                case Conjugation.DICTIONARY:
                    return [b + "らしい" for b in bases]
                case Conjugation.TE:
                    return [b + "らしくて" for b in bases]
                case _:
                    raise ValueError(f"Unhandled conjugation for rashii: {conj}")
        
        case Auxiliary.SOUDA_HEARSAY:
            base1 = conjugate(verb, Conjugation.TA, type2)[0]
            base2 = verb
            match conj:
                case Conjugation.DICTIONARY:
                    return [base1 + "そうだ", base2 + "そうだ"]
                case _:
                    raise ValueError(f"Unhandled conjugation for souda (hearsay): {conj}")
        
        case Auxiliary.SOUDA_CONJECTURE:
            base = conjugate(verb, Conjugation.CONJUNCTIVE, type2)[0]
            match conj:
                case Conjugation.DICTIONARY:
                    return [base + "そうだ", base + "そうです"]
                case Conjugation.CONDITIONAL:
                    return [base + "そうなら"]
                case Conjugation.TA:
                    return [base + "そうだった", base + "そうでした"]
                case _:
                    raise ValueError(f"Unhandled conjugation for souda (conjecture): {conj}")
        
        case Auxiliary.SERU_SASERU | Auxiliary.SHORTENED_CAUSATIVE:
            if conj in (Conjugation.TARA, Conjugation.TARI):
                raise ValueError(f"Unhandled conjugation for causative: {conj}")
            
            if verb in ("来る", "くる"):
                prefix = "来" if verb[0] == "来" else "こ"
                new_verb = prefix + "させる"
            elif verb == "する":
                new_verb = "させる"
            elif type2:
                new_verb = _conjugate_type2(verb, Conjugation.NEGATIVE)[0] + "させる"
            else:
                new_verb = _conjugate_type1(verb, Conjugation.NEGATIVE)[0] + "せる"
            
            if aux == Auxiliary.SHORTENED_CAUSATIVE:
                new_verb = new_verb[:-2] + "す"
                return conjugate(new_verb, conj, type2=False)
            return conjugate(new_verb, conj, type2=True)
        
        case Auxiliary.RERU_RARERU:
            # Now supports CONDITIONAL for chains like 言われてみれば
            if conj in (Conjugation.IMPERATIVE, Conjugation.VOLITIONAL,
                       Conjugation.TARA, Conjugation.TARI):
                raise ValueError(f"Unhandled conjugation for passive/potential: {conj}")
            
            if verb in ("来る", "くる"):
                prefix = "来" if verb[0] == "来" else "こ"
                new_verb = prefix + "られる"
            elif verb == "する":
                new_verb = "される"
            elif type2:
                new_verb = _conjugate_type2(verb, Conjugation.NEGATIVE)[0] + "られる"
            else:
                new_verb = _conjugate_type1(verb, Conjugation.NEGATIVE)[0] + "れる"
            return conjugate(new_verb, conj, type2=True)
        
        case Auxiliary.CAUSATIVE_PASSIVE:
            causative = _conjugate_auxiliary(verb, Auxiliary.SERU_SASERU, Conjugation.NEGATIVE, type2)[0]
            new_verb = causative + "られる"
            return conjugate(new_verb, conj, type2=True)
        
        case Auxiliary.SHORTENED_CAUSATIVE_PASSIVE:
            causative = _conjugate_auxiliary(verb, Auxiliary.SHORTENED_CAUSATIVE, Conjugation.NEGATIVE, type2)[0]
            new_verb = causative + "れる"
            return conjugate(new_verb, conj, type2=True)
        
        case (Auxiliary.AGERU | Auxiliary.SASHIAGERU | Auxiliary.YARU |
              Auxiliary.MORAU | Auxiliary.ITADAKU | Auxiliary.KURERU |
              Auxiliary.KUDASARU | Auxiliary.TE_IRU | Auxiliary.TE_ARU |
              Auxiliary.MIRU | Auxiliary.IKU | Auxiliary.KURU |
              Auxiliary.OKU | Auxiliary.TE_ORU):
            vte = conjugate(verb, Conjugation.TE, type2)[0]
            
            endings = {
                Auxiliary.AGERU: ["あげる"],
                Auxiliary.SASHIAGERU: ["差し上げる", "さしあげる"],
                Auxiliary.YARU: ["やる"],
                Auxiliary.MORAU: ["もらう"],
                Auxiliary.ITADAKU: ["いただく"],
                Auxiliary.KURERU: ["くれる"],
                Auxiliary.KUDASARU: ["くださる"],
                Auxiliary.TE_IRU: ["いる", "る"],
                Auxiliary.TE_ARU: ["ある"],
                Auxiliary.MIRU: ["みる"],
                Auxiliary.IKU: ["いく"],
                Auxiliary.KURU: ["くる"],
                Auxiliary.OKU: ["おく"],
                Auxiliary.TE_ORU: ["おる"],
            }[aux]
            
            if aux == Auxiliary.KURU:
                return [vte + suffix for suffix in conjugate("くる", conj)]
            
            ending_type2 = aux in (
                Auxiliary.AGERU, Auxiliary.SASHIAGERU, Auxiliary.KURERU,
                Auxiliary.TE_IRU, Auxiliary.MIRU
            )
            
            new_verbs = [vte + ending for ending in endings]
            
            # Add contracted forms
            if aux == Auxiliary.OKU:
                contracted = vte[:-1] + ("どく" if vte[-1] == "で" else "とく")
                new_verbs.append(contracted)
            elif aux == Auxiliary.IKU:
                new_verbs.append(vte + "く")
            
            results = []
            for v in new_verbs:
                results.extend(conjugate(v, conj, type2=ending_type2))
            return results
        
        case Auxiliary.SHIMAU:
            vte = conjugate(verb, Conjugation.TE, type2)[0]
            shimau = conjugate(vte + "しまう", conj)
            no_te = vte[:-1]
            
            # Colloquial contractions
            if vte.endswith("て"):
                chau = conjugate(no_te + "ちゃう", conj)
                chimau = conjugate(no_te + "ちまう", conj)
                return shimau + chau + chimau
            else:  # で ending - rendaku
                jimau = conjugate(no_te + "じまう", conj)
                dimau = conjugate(no_te + "ぢまう", conj)
                return shimau + jimau + dimau
        
        case _:
            raise ValueError(f"Unhandled auxiliary: {aux}")


def conjugate_auxiliaries(
    verb: str,
    auxiliaries: list[Auxiliary],
    final_conj: Conjugation,
    type2: bool = False,
) -> list[str]:
    """Conjugate a verb with a chain of auxiliaries.
    
    This handles complex chains like 食べられなかった (potential + nai + past).
    
    Args:
        verb: Dictionary form of the verb
        auxiliaries: List of auxiliaries to apply in order
        final_conj: Final conjugation form
        type2: True for ichidan verbs
    
    Returns:
        List of conjugated forms
    
    Examples:
        >>> conjugate_auxiliaries("食べる", [Auxiliary.RERU_RARERU, Auxiliary.NAI], 
        ...                        Conjugation.TA, type2=True)
        ['食べられなかった']
    """
    if not auxiliaries:
        return conjugate(verb, final_conj, type2)
    
    # Handle copula with nai
    if verb in ("だ", "です"):
        if len(auxiliaries) == 1 and auxiliaries[0] == Auxiliary.NAI:
            if final_conj == Conjugation.TA:
                if verb == "だ":
                    return ["ではなかった", "じゃなかった"]
                return ["ではありませんでした", "でありませんでした"]
            elif final_conj == Conjugation.TE and verb == "だ":
                return ["じゃなくて"]
            elif final_conj == Conjugation.CONJUNCTIVE and verb == "だ":
                return ["じゃなく"]
        raise ValueError("Unhandled copula auxiliaries/conjugation")
    
    verbs = [verb]
    current_type2 = type2
    
    for i, aux in enumerate(auxiliaries):
        conj = final_conj if i == len(auxiliaries) - 1 else Conjugation.DICTIONARY
        prev_aux = auxiliaries[i - 1] if i > 0 else None
        
        # Validate final-only auxiliaries
        if i != len(auxiliaries) - 1:
            final_only = (
                Auxiliary.MASU, Auxiliary.NAI, Auxiliary.TAI,
                Auxiliary.HOSHII, Auxiliary.RASHII,
                Auxiliary.SOUDA_CONJECTURE, Auxiliary.SOUDA_HEARSAY
            )
            if aux in final_only:
                raise ValueError(f"{aux} must be final auxiliary")
        
        # Handle kuru as previous auxiliary
        if prev_aux == Auxiliary.KURU:
            heads = [s[:-2] for s in verbs]
            tails = _conjugate_auxiliary("くる", aux, conj)
            verbs = [head + tail for head in heads for tail in tails]
        else:
            new_verbs = []
            for v in verbs:
                new_verbs.extend(_conjugate_auxiliary(v, aux, conj, current_type2))
            verbs = new_verbs
        
        # Update type2 for next iteration
        current_type2 = aux in (
            Auxiliary.POTENTIAL, Auxiliary.SERU_SASERU,
            Auxiliary.RERU_RARERU, Auxiliary.CAUSATIVE_PASSIVE,
            Auxiliary.SHORTENED_CAUSATIVE_PASSIVE, Auxiliary.AGERU,
            Auxiliary.SASHIAGERU, Auxiliary.KURERU, Auxiliary.MIRU,
            Auxiliary.TE_IRU
        )
    
    return verbs


@dataclass(frozen=True, slots=True)
class VerbDeconjugated:
    """Result of verb deconjugation."""
    
    auxiliaries: tuple[Auxiliary, ...]
    conjugation: Conjugation
    result: list[str]


def deconjugate_verb(
    conjugated: str,
    dictionary_form: str,
    type2: bool = False,
    max_aux_depth: int = 3,
) -> list[VerbDeconjugated]:
    """Identify the conjugation form(s) of a conjugated verb.
    
    This function attempts to find what conjugation chain could
    produce the given conjugated form from the dictionary form.
    
    Args:
        conjugated: The conjugated form to analyze
        dictionary_form: The dictionary form of the verb
        type2: True for ichidan verbs
        max_aux_depth: Maximum auxiliary chain depth to search (1-3)
    
    Returns:
        List of matching VerbDeconjugated results
    
    Examples:
        >>> results = deconjugate_verb("食べられなかった", "食べる", type2=True)
        >>> # Should find RERU_RARERU + NAI with TA conjugation
    """
    hits: list[VerbDeconjugated] = []
    
    # Depth 0: Direct conjugations
    for conj in Conjugation:
        try:
            result = conjugate(dictionary_form, conj, type2)
            if conjugated in result:
                hits.append(VerbDeconjugated(
                    auxiliaries=(),
                    conjugation=conj,
                    result=result,
                ))
        except ValueError:
            pass
    
    if max_aux_depth < 1:
        return hits
    
    # Depth 1: Single auxiliary
    for aux in Auxiliary:
        for conj in Conjugation:
            try:
                result = _conjugate_auxiliary(dictionary_form, aux, conj, type2)
                if conjugated in result:
                    hits.append(VerbDeconjugated(
                        auxiliaries=(aux,),
                        conjugation=conj,
                        result=result,
                    ))
            except ValueError:
                pass
    
    if max_aux_depth < 2:
        return hits
    
    # Depth 2: Two auxiliaries
    # First set: aux chains ending in final-only auxiliaries
    penultimates = [
        Auxiliary.AGERU, Auxiliary.SASHIAGERU, Auxiliary.YARU,
        Auxiliary.MORAU, Auxiliary.ITADAKU, Auxiliary.KURERU,
        Auxiliary.KUDASARU, Auxiliary.MIRU, Auxiliary.IKU,
        Auxiliary.KURU, Auxiliary.OKU, Auxiliary.SHIMAU,
        Auxiliary.TE_IRU, Auxiliary.TE_ARU, Auxiliary.TE_ORU,
        Auxiliary.POTENTIAL, Auxiliary.RERU_RARERU, Auxiliary.SERU_SASERU,
    ]
    depth2_finals = [
        Auxiliary.MASU, Auxiliary.SOUDA_CONJECTURE, Auxiliary.SOUDA_HEARSAY,
        Auxiliary.TE_IRU, Auxiliary.TAI, Auxiliary.NAI, Auxiliary.YARU,
        Auxiliary.MIRU, Auxiliary.OKU, Auxiliary.SHIMAU,  # Added these for chains like passive+miru
    ]
    
    for penultimate in penultimates:
        for final in depth2_finals:
            for conj in Conjugation:
                try:
                    auxs = [penultimate, final]
                    result = conjugate_auxiliaries(dictionary_form, auxs, conj, type2)
                    if conjugated in result:
                        hits.append(VerbDeconjugated(
                            auxiliaries=tuple(auxs),
                            conjugation=conj,
                            result=result,
                        ))
                except ValueError:
                    pass
    
    if max_aux_depth < 3:
        return hits
    
    # Depth 3: Three auxiliaries
    antepenultimates = [Auxiliary.SERU_SASERU, Auxiliary.RERU_RARERU, Auxiliary.ITADAKU]
    depth3_finals = [Auxiliary.MASU]
    
    for ante in antepenultimates:
        for penultimate in penultimates:
            for final in depth3_finals:
                for conj in Conjugation:
                    try:
                        auxs = [ante, penultimate, final]
                        result = conjugate_auxiliaries(dictionary_form, auxs, conj, type2)
                        if conjugated in result:
                            hits.append(VerbDeconjugated(
                                auxiliaries=tuple(auxs),
                                conjugation=conj,
                                result=result,
                            ))
                    except ValueError:
                        pass
    
    return hits


# Convenience function
def identify_verb_type(verb: str) -> bool:
    """Attempt to identify if a verb is Type II (ichidan).
    
    This is a heuristic - use dictionary data for accuracy.
    
    Returns:
        True if likely ichidan, False if likely godan
    """
    # Common ichidan patterns
    if verb.endswith("る"):
        pre_ru = verb[-2] if len(verb) >= 2 else ""
        # Ichidan if preceded by i-dan or e-dan vowels
        return pre_ru in "いきしちにひみりぎじびぴえけせてねへめれげぜべぺ"
    return False
