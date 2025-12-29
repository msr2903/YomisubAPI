
import sys
import time
from pathlib import Path
import json

# Add src to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analysis import analyze_text, analyze_full
from services.analyzer import JapaneseAnalyzer

def run_tests():
    print("Initializing Analyzer (loading dictionaries)...")
    start_init = time.time()
    JapaneseAnalyzer.get_instance()
    print(f"Initialization took {time.time() - start_init:.4f}s")

    test_cases = [
        {
            "desc": "Standard Polite Sentence",
            "text": "昨日は友達と映画を見に行きました。"
        },
        {
            "desc": "Name Detection (JMNedict)",
            "text": "田中さんは東京に住んでいます。"
        },
        {
            "desc": "Complex Conjugation Chain (Causative-Passive-Sou-Past)",
            "text": "腐った納豆を食べさせられそうになりました。"
        },
        {
            "desc": "Must-do Grammar (Negative Conditional + Narana)",
            "text": "明日は早く起きなければなりません。"
        },
        {
            "desc": "Te-form Request Chain (Try doing + want)",
            "text": "この本を読んでみてほしいです。"
        },
        {
            "desc": "Casual Slang",
            "text": "それ、マジでやばくない？"
        }
    ]

    print("\nRunning Complex Analysis Tests...\n")
    
    for case in test_cases:
        print(f"=== {case['desc']} ===")
        print(f"Input: {case['text']}")
        
        start = time.perf_counter()
        result = analyze_text(case['text'])
        end = time.perf_counter()
        
        print(f"Time: {(end - start) * 1000:.2f}ms")
        print("Tokens:")
        for token in result.tokens:
            base_info = f"{token.word} ({token.reading})"
            if token.base != token.word:
                base_info += f" -> {token.base}"
            
            meaning = f" [{token.meaning[:30]}...]" if token.meaning else ""
            pos = f" <{token.pos}>"
            
            extra = []
            if token.conjugation:
                extra.append(f"Conj: {token.conjugation.summary}")
                if token.conjugation.translation_hint:
                    extra.append(f"Hint: {token.conjugation.translation_hint}")
            
            if token.tags:
                extra.append(f"Tags: {', '.join(token.tags)}")
                
            extra_str = f" | {' '.join(extra)}" if extra else ""
            
            print(f"  - {base_info}{pos}{meaning}{extra_str}")
            
            if token.components:
                 for comp in token.components:
                     print(f"    - {comp.surface} ({comp.base}) [{comp.pos}]")
        print("\n" + "-" * 40 + "\n")

    print("Tests Complete.")

if __name__ == "__main__":
    run_tests()
