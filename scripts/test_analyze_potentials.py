import sys
from pathlib import Path

# Add src to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.analyzer import JapaneseAnalyzer
from services.analysis import analyze_text

def test_full_analysis_potentials():
    # Initialize analyzer
    JapaneseAnalyzer.get_instance()
    
    test_sentences = [
        "刺身が食べれる。",
        "テレビが見れない。",
        "早く起きれた！",
        "信じられないことが起きた。",
        "日本語が教えれます。",
        "もう辞めれません。",
        "その服が着れる？",
        "お金が借りれた。",
        "ドアが閉めれない。",
        "信じれるよ。",
        "覚えれない？",
        "すぐ辞めれる。",
        "ここから逃げれる。",
    ]

    print(f"{'Sentence':<20} | {'Word':<10} | {'Base Found':<10} | {'Conjugation Summary'}")
    print("-" * 80)

    for sentence in test_sentences:
        res = analyze_text(sentence)
        for token in res.tokens:
            # Look for the verb tokens
            if token.conjugation:
                print(f"{sentence:<20} | {token.word:<10} | {token.base:<10} | {token.conjugation.summary}")

if __name__ == "__main__":
    test_full_analysis_potentials()
