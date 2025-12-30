
import sys
sys.path.insert(0, 'src')

from services.analysis import process_pro, process_lite, process_ultra
from services.conjugation.helpers import detect_godan_potential

def test_godan_potential():
    test_words = [
        "飲める", "書ける", "話せる", "待てる", "読める", "買える", "作れる"
    ]
    
    print("--- 1. Testing Helper Detection ---")
    for word in test_words:
        result = detect_godan_potential(word, word)
        if result:
            print(f"✓ {word} -> {result[0]}")
        else:
            print(f"✗ {word} -> Not detected")
            
    print("\n--- 2. Testing API Processing (analyze_pro) ---")
    for word in test_words:
        print(f"\nAnalyzing: {word}")
        try:
            result = process_pro(word)
            if not result.phrases:
                print("  No tokens found")
                continue
                
            token = result.phrases[0]
            print(f"  Surface: {token.surface}")
            print(f"  Base:    {token.base}")
            print(f"  Meaning: {token.meaning[:50]}...")
            if token.conjugation:
                print(f"  Conj:    {token.conjugation.summary}")
            else:
                print("  Conj:    None")
                
            # Verify
            is_potential = (token.conjugation and "potential" in token.conjugation.summary)
            if is_potential and token.base != word:
                print(f"  ✅ SUCCESS: Recognized as potential form of {token.base}")
            else:
                print(f"  ❌ FAILURE: {token.base} / {token.conjugation.summary if token.conjugation else 'None'}")
                
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    test_godan_potential()
