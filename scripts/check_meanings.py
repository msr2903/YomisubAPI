
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))
from services.analyzer import JapaneseAnalyzer

print("Loading JMdict...")
analyzer = JapaneseAnalyzer.get_instance()
jmdict = analyzer._jmdict

words = ["だ", "です"]
for w in words:
    d = jmdict.lookup_details(w)
    if d:
        print(f"Word: {w}")
        print(f"Meanings: {d.get('meanings')}")
    else:
        print(f"Word: {w} - Not found")
