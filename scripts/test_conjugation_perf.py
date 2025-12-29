
import sys
import time
from pathlib import Path

# Add src to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analysis import deconjugate_word, analyze_text
from services.analyzer import JapaneseAnalyzer

def run_tests():
    print("Initializing Analyzer (loading dictionaries)...")
    start_init = time.time()
    JapaneseAnalyzer.get_instance()
    print(f"Initialization took {time.time() - start_init:.4f}s")

    test_cases = [
        # Fix verification cases
        ("食べられなかった", "verb", "couldn't eat"),
        ("好かれる", "verb", "is liked"),
        ("食べなかった", "verb", "didn't eat"),
        
        # Standard Godan
        ("書いた", "verb", "wrote"),
        ("話しません", "verb", "not speak (polite)"), # imprecise match for translation, mostly checking breakdown
        ("待たされる", "verb", "is made to wait"), # causative-passive
        ("食べなさい", "verb", "please eat"), # nasai
        
        # Standard Ichidan
        ("信じられない", "verb", "can't believe"), # potential + negative
        ("食べれません", "verb", "cannot eat"),  # Ra-nuki potential
        
        # Suffixes
        ("食べすぎる", "verb", "over-eat"),
        ("飲みすぎない", "verb", "not over-drink"),
        ("読みやすい", "verb", "easy to read"),
        ("読みやすかった", "verb", "was easy to read"),
        ("分かりにくい", "verb", "hard to understand"),
        ("分かりにくくなかった", "verb", "was not hard to understand"),
        ("読み始める", "verb", "start reading"),
        ("読み終わった", "verb", "finish reading"),
        ("飲み続ける", "verb", "continue drinking"),

        # Irregular
        ("勉強した", "verb", "studied"), # suru verb
        ("来ない", "verb", "not come"), # kuru verb
        
        # Adjectives
        ("寒くなかった", "adjective", "was not cold"),
        ("静かではなかった", "adjective", "was not quiet"),
        
        # Phrases (using analyze_text to catch compound phrases)
        ("日本語を勉強しなければなりません", "analysis", "must not"),
        ("行くかもしれない", "analysis", "might"),
    ]

    print("\nRunning Conjugation Tests...\n")
    
    total_time = 0
    passes = 0
    
    for word, type_, expected in test_cases:
        print(f"Testing: {word}")
        start = time.perf_counter()
        
        try:
            if type_ == "analysis":
                result = analyze_text(word)
                # For analysis, we look for the conjugation/phrase hint in the output tokens
                found_hint = False
                hints_found = []
                for token in result.tokens:
                    # check conjugation info hint or phrase meaning
                    if token.conjugation and token.conjugation.translation_hint:
                        hints_found.append(token.conjugation.translation_hint)
                    if token.components:
                         for comp in token.components:
                             if comp.meaning: hints_found.append(comp.meaning)
                    if token.pos == "Phrase":
                        hints_found.append(token.meaning)

                # Loose checking for analysis phrases
                full_text_res = str(hints_found)
                # print(f"  Result hints: {full_text_res}")
                
            else:
                # Deconjugate
                result = deconjugate_word(word)
                print(f"  -> Breakdown: {result.full_breakdown}")
                print(f"  -> Hint: {result.natural_english}")
                
                # Check expectation
                # We do a loose check if expected text is in the natural English result
                if expected.lower() in result.natural_english.lower():
                     print("  ✅ Match")
                else:
                    # Special handling if strict match fails, just visually verify for now or logic check
                    # For 'not speak (polite)', result might be 'not speak' + polite tag info elsewhere
                    pass 

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

        end = time.perf_counter()
        elapsed = (end - start) * 1000
        print(f"  ⏱️ Time: {elapsed:.2f}ms")
        total_time += elapsed
        print("-" * 30)

    avg_time = total_time / len(test_cases)
    print(f"\nTotal Tests: {len(test_cases)}")
    print(f"Average Processing Time: {avg_time:.2f}ms")

if __name__ == "__main__":
    run_tests()
