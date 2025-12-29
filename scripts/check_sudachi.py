
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))
from services.analyzer import JapaneseAnalyzer
from sudachipy import SplitMode

# Initialize (loads dicts, might take time)
print("Initializing analyzer...")
analyzer = JapaneseAnalyzer.get_instance()
tokenizer_obj = analyzer._tokenizer
mode = SplitMode.C

words = ["読み始める", "読み終わった", "飲み続ける", "読みやすかった"]

print("Checking Sudachi Tokenization:")
for w in words:
    tokens = tokenizer_obj.tokenize(w, mode)
    if tokens:
        m = tokens[0]
        print(f"Word: {w}")
        print(f"  Dict Form: {m.dictionary_form()}")
        print(f"  POS: {m.part_of_speech()}")
        print(f"  Reading: {m.reading_form()}")
        print(f"  Tokens: {[t.surface() for t in tokens]}")
    else:
        print(f"Word: {w} - No tokens")
    print("-" * 20)
