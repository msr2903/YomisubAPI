#!/usr/bin/env python3
"""Test copula compound phrase matching with full analysis."""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analysis import process_pro

test_sentences = [
    "私は学生ではありません",
    "彼は先生ではなかった", 
    "これはペンではありませんでした",
    "明日は雨でしょう",
    "彼は来るだろう",
    "私は日本人じゃない",
    "それは本である",
    "これは問題であります",
]

print("Testing process_pro with copula phrases")
print("="*60)

for sentence in test_sentences:
    print(f"\n=== {sentence} ===")
    result = process_pro(sentence)
    for phrase in result.phrases:
        pos = phrase.pos
        base = phrase.base
        meaning = phrase.meaning or ""
        grammar = phrase.grammar_note or ""
        
        print(f"  {phrase.surface}")
        print(f"    Base: {base}")
        print(f"    POS: {pos}")
        if meaning:
            print(f"    Meaning: {meaning}")
        if grammar:
            print(f"    Grammar: {grammar}")
        if phrase.conjugation and phrase.conjugation.chain:
            print(f"    Conjugation Layers:")
            for i, layer in enumerate(phrase.conjugation.chain, 1):
                print(f"      {i}. {layer.english} ({layer.meaning})")
            print(f"    Summary: {phrase.conjugation.summary}")
            print(f"    Hint: {phrase.conjugation.translation_hint}")
