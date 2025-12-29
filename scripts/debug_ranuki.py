
import sys
from pathlib import Path
from sudachipy import Dictionary, SplitMode

# Add src to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analysis import analyze_text, deconjugate_word
from services.verb import deconjugate_verb

def debug_ranuki():
    print("--- Debugging Ra-nuki (食べれません) ---")
    text = "食べれません"
    
    tokenizer = Dictionary(dict="full").create()
    
    # Check Sudachi tokenization
    print("Sudachi SplitMode.A:")
    for m in tokenizer.tokenize(text, SplitMode.A):
        print(f"  {m.surface()} -> {m.dictionary_form()} {m.part_of_speech()}")
        
    print("Sudachi SplitMode.C:")
    for m in tokenizer.tokenize(text, SplitMode.C):
        print(f"  {m.surface()} -> {m.dictionary_form()} {m.part_of_speech()}")
        
    # Run full analysis
    print("\nRunning analyze_text...")
    # We need to initialize analyzer first (it loads JMDict)
    from services.analyzer import JapaneseAnalyzer
    JapaneseAnalyzer.get_instance()
    
    res = analyze_text(text)
    for token in res.tokens:
        print(f"Token: {token.word} -> {token.base}")
        print(f"Meaning: {token.meaning}")
        print(f"Conjugation: {token.conjugation}")
        if token.conjugation:
             print(f"  Summary: {token.conjugation.summary}")
             print(f"  Hint: {token.conjugation.translation_hint}")

if __name__ == "__main__":
    debug_ranuki()
