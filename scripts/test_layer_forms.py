
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analysis import deconjugate_word

def test_breakdown_forms():
    words = ["読みにくかった", "食べさせられた"]
    
    print("Testing Breakdown Forms:\n")
    
    for word in words:
        print(f"Word: {word}")
        try:
            # We need to initialize analyzer for this to really work
            from services.analyzer import JapaneseAnalyzer
            JapaneseAnalyzer.get_instance()
            
            result = deconjugate_word(word)
            if result.layers:
                for i, layer in enumerate(result.layers):
                    print(f"  Layer {i+1}:")
                    print(f"    Type: {layer.type}")
                    print(f"    Form: {layer.form}  <-- This is what we added")
                    print(f"    Meaning: {layer.meaning}")
            else:
                 print("  No layers found.")

        except Exception as e:
            print(f"  Error: {e}")
        print("-" * 30)

if __name__ == "__main__":
    test_breakdown_forms()
