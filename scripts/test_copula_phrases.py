#!/usr/bin/env python3
"""Test copula compound phrase matching."""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analyzer import JapaneseAnalyzer
from services.conjugation.phrases import try_match_compound_phrase, COMPOUND_PHRASES
from sudachipy import SplitMode

print("Initializing analyzer...")
analyzer = JapaneseAnalyzer.get_instance()
tokenizer_obj = analyzer._tokenizer
mode = SplitMode.C

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

print("\n" + "="*60)
print("Testing tokenization and phrase matching")
print("="*60)

for sentence in test_sentences:
    print(f"\n=== {sentence} ===")
    morphemes = tokenizer_obj.tokenize(sentence, mode)
    
    print("Tokens:")
    for i, m in enumerate(morphemes):
        print(f"  [{i}] '{m.surface()}' (pos: {m.part_of_speech()[0]}, dict: {m.dictionary_form()})")
    
    print("\nPhrase matching:")
    for i, m in enumerate(morphemes):
        match = try_match_compound_phrase(list(morphemes), i)
        if match:
            phrase, meaning, consumed = match
            print(f"  At [{i}] '{m.surface()}' -> MATCH: '{phrase}' = {meaning} (consumes {consumed} tokens)")
