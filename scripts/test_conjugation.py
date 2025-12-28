#!/usr/bin/env python3
"""Test script for verb and adjective conjugation/deconjugation.

Tests complex forms like:
- 食べられなかった (potential/passive + negative + past)
- 言われてみれば (passive + te + miru + conditional)
"""

import sys
import importlib.util
from pathlib import Path

# Load modules directly without going through services __init__.py
src_dir = Path(__file__).parent.parent / "src" / "services"

def load_module(name: str, path: Path):
    """Load a module from a specific path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

verb_module = load_module("verb", src_dir / "verb.py")
adjective_module = load_module("adjective", src_dir / "adjective.py")

# Import needed items
Conjugation = verb_module.Conjugation
Auxiliary = verb_module.Auxiliary
conjugate = verb_module.conjugate
conjugate_auxiliaries = verb_module.conjugate_auxiliaries
deconjugate_verb = verb_module.deconjugate_verb

AdjConjugation = adjective_module.AdjConjugation
conjugate_adjective = adjective_module.conjugate_adjective
deconjugate_adjective = adjective_module.deconjugate_adjective


def test_verb_conjugation():
    """Test basic verb conjugation."""
    print("=" * 60)
    print("VERB CONJUGATION TESTS")
    print("=" * 60)
    
    # Test 食べる (ichidan)
    print("\n食べる (to eat) - ichidan verb:")
    for conj in [Conjugation.NEGATIVE, Conjugation.TE, Conjugation.TA]:
        result = conjugate("食べる", conj, type2=True)
        print(f"  {conj.name}: {result}")
    
    # Test 書く (godan)
    print("\n書く (to write) - godan verb:")
    for conj in [Conjugation.NEGATIVE, Conjugation.TE, Conjugation.TA]:
        result = conjugate("書く", conj, type2=False)
        print(f"  {conj.name}: {result}")
    
    # Test する (irregular)
    print("\nする (to do) - irregular:")
    for conj in [Conjugation.NEGATIVE, Conjugation.TE, Conjugation.TA]:
        result = conjugate("する", conj)
        print(f"  {conj.name}: {result}")
    
    # Test くる (irregular)
    print("\nくる (to come) - irregular:")
    for conj in [Conjugation.NEGATIVE, Conjugation.TE, Conjugation.TA]:
        result = conjugate("くる", conj)
        print(f"  {conj.name}: {result}")


def test_auxiliary_conjugation():
    """Test verb conjugation with auxiliaries."""
    print("\n" + "=" * 60)
    print("AUXILIARY CONJUGATION TESTS")
    print("=" * 60)
    
    # 食べられる (potential/passive of 食べる)
    print("\n食べる + potential/passive:")
    result = conjugate_auxiliaries("食べる", [Auxiliary.RERU_RARERU], Conjugation.DICTIONARY, type2=True)
    print(f"  Dictionary: {result}")
    
    # 食べられない (potential/passive + negative)
    result = conjugate_auxiliaries("食べる", [Auxiliary.RERU_RARERU, Auxiliary.NAI], Conjugation.DICTIONARY, type2=True)
    print(f"  Negative: {result}")
    
    # 食べられなかった (potential/passive + negative + past)
    print("\n★ 食べられなかった (couldn't eat):")
    result = conjugate_auxiliaries("食べる", [Auxiliary.RERU_RARERU, Auxiliary.NAI], Conjugation.TA, type2=True)
    print(f"  Result: {result}")
    print(f"  ✓ Contains 食べられなかった: {'食べられなかった' in result}")
    
    # 言われる (passive of 言う)
    print("\n言う + passive:")
    result = conjugate_auxiliaries("言う", [Auxiliary.RERU_RARERU], Conjugation.DICTIONARY, type2=False)
    print(f"  Dictionary: {result}")
    
    # 言われて (passive + te)
    result = conjugate_auxiliaries("言う", [Auxiliary.RERU_RARERU], Conjugation.TE, type2=False)
    print(f"  Te-form: {result}")
    
    # 言われてみる (passive + te + miru)
    print("\n言う + passive + miru:")
    result = conjugate_auxiliaries("言う", [Auxiliary.RERU_RARERU, Auxiliary.MIRU], Conjugation.DICTIONARY, type2=False)
    print(f"  Dictionary: {result}")
    
    # 言われてみれば (passive + te + miru + conditional)
    print("\n★ 言われてみれば (when you think about it):")
    result = conjugate_auxiliaries("言う", [Auxiliary.RERU_RARERU, Auxiliary.MIRU], Conjugation.CONDITIONAL, type2=False)
    print(f"  Result: {result}")
    print(f"  ✓ Contains 言われてみれば: {'言われてみれば' in result}")


def test_deconjugation():
    """Test verb deconjugation (reverse lookup)."""
    print("\n" + "=" * 60)
    print("DECONJUGATION TESTS")
    print("=" * 60)
    
    # Test 食べられなかった
    print("\n★ Deconjugating 食べられなかった:")
    results = deconjugate_verb("食べられなかった", "食べる", type2=True)
    if results:
        for r in results:
            auxs = " + ".join(a.name for a in r.auxiliaries) if r.auxiliaries else "(none)"
            print(f"  Auxiliaries: {auxs}")
            print(f"  Conjugation: {r.conjugation.name}")
    else:
        print("  No matches found!")
    
    # Test 言われてみれば  
    print("\n★ Deconjugating 言われてみれば:")
    results = deconjugate_verb("言われてみれば", "言う", type2=False)
    if results:
        for r in results:
            auxs = " + ".join(a.name for a in r.auxiliaries) if r.auxiliaries else "(none)"
            print(f"  Auxiliaries: {auxs}")
            print(f"  Conjugation: {r.conjugation.name}")
    else:
        print("  No matches found!")
    
    # Test simple forms
    print("\n食べた (simple past):")
    results = deconjugate_verb("食べた", "食べる", type2=True)
    for r in results:
        print(f"  Conjugation: {r.conjugation.name}")
    
    print("\n書いて (te-form of 書く):")
    results = deconjugate_verb("書いて", "書く", type2=False)
    for r in results:
        print(f"  Conjugation: {r.conjugation.name}")


def test_adjective_conjugation():
    """Test adjective conjugation."""
    print("\n" + "=" * 60)
    print("ADJECTIVE CONJUGATION TESTS")
    print("=" * 60)
    
    # Test i-adjective: 高い
    print("\n高い (tall/expensive) - i-adjective:")
    for conj in [AdjConjugation.PRESENT, AdjConjugation.NEGATIVE, 
                 AdjConjugation.PAST, AdjConjugation.NEGATIVE_PAST]:
        result = conjugate_adjective("高い", conj, is_i_adjective=True)
        print(f"  {conj.name}: {result}")
    
    # Test na-adjective: 静か
    print("\n静か (quiet) - na-adjective:")
    for conj in [AdjConjugation.PRESENT, AdjConjugation.PRENOMINAL,
                 AdjConjugation.NEGATIVE, AdjConjugation.PAST]:
        result = conjugate_adjective("静か", conj, is_i_adjective=False)
        print(f"  {conj.name}: {result}")
    
    # Test irregular いい
    print("\nいい/良い (good) - irregular i-adjective:")
    for conj in [AdjConjugation.PRESENT, AdjConjugation.NEGATIVE,
                 AdjConjugation.PAST, AdjConjugation.NEGATIVE_PAST]:
        result = conjugate_adjective("いい", conj, is_i_adjective=True)
        print(f"  {conj.name}: {result}")


def test_adjective_deconjugation():
    """Test adjective deconjugation."""
    print("\n" + "=" * 60)
    print("ADJECTIVE DECONJUGATION TESTS")
    print("=" * 60)
    
    print("\n高くなかった -> 高い:")
    results = deconjugate_adjective("高くなかった", "高い", is_i_adjective=True)
    for r in results:
        print(f"  Conjugation: {r.conjugation.name}")
    
    print("\n静かではなかった -> 静か:")
    results = deconjugate_adjective("静かではなかった", "静か", is_i_adjective=False)
    for r in results:
        print(f"  Conjugation: {r.conjugation.name}")


def main():
    """Run all tests."""
    test_verb_conjugation()
    test_auxiliary_conjugation()
    test_deconjugation()
    test_adjective_conjugation()
    test_adjective_deconjugation()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
