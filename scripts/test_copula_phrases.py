#!/usr/bin/env python3
"""Test copula compound phrase matching with full analysis."""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analysis import analyze_full

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

print("Testing analyze_full with copula phrases")
print("="*60)

for sentence in test_sentences:
    print(f"\n=== {sentence} ===")
    result = analyze_full(sentence)
    for phrase in result.phrases:
        meaning = phrase.meaning or phrase.grammar_note or ""
        if meaning:
            print(f"  {phrase.surface} [{phrase.pos}] = {meaning}")
        else:
            print(f"  {phrase.surface} [{phrase.pos}]")
