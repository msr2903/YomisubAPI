
import sys
import os

# Add src to python path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.analyzer import JapaneseAnalyzer

def print_token(t, indent_level=0):
    indent = "  " * indent_level
    print(f"{indent}Token: [{t.surface}]")
    print(f"{indent}  Base: {t.base_form}")
    print(f"{indent}  POS: {t.pos}")
    print(f"{indent}  Meaning: {t.meaning}")
    if t.components:
        print(f"{indent}  --- Components ({len(t.components)}) ---")
        for c in t.components:
            print_token(c, indent_level + 1)
        print(f"{indent}  -----------------------")

def test_boundaries():
    print("Initializing Analyzer...")
    analyzer = JapaneseAnalyzer.get_instance()
    
    # Test cases designed to check boundaries
    test_cases = [
        # Case 1: Complex verb group + Noun
        # 食べられなかった (Could not eat) + 寿司 (Sushi)
        "食べられなかった寿司",
        
        # Case 2: Chain with helper verb + Adjective
        # 言われてみれば (If I try saying/If you ask me) + 難しい (Difficult)
        "言われてみれば難しい",
        
        # Case 3: Te-form helper (continuous state) + Noun
        # 走っている (Is running) + 犬 (Dog)
        "走っている犬",
        
        # Case 4: Adjective conjugation + Noun
        # 美味しくなかった (Was not delicious) + 料理 (Food)
        "美味しくなかった料理",
        
        # Case 5: Standard sentence structure
        # ご飯を食べた後 (After I ate the meal)
        "ご飯を食べた後",
    ]
    
    for text in test_cases:
        print(f"\n{'='*60}")
        print(f"Input Text: 「{text}」")
        print(f"{'='*60}")
        
        tokens = analyzer.analyze(text)
        
        for i, t in enumerate(tokens):
            print(f"\n[Main Token {i+1}]")
            print_token(t)

if __name__ == "__main__":
    test_boundaries()
